import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  saveGATEDetails,
  savePersonalDetails,
  saveBranchPreferences,
  saveLocationPreferences,
  saveConstraints,
  getProfile,
  uploadCV,
  confirmCV,
} from "../services/api";

const STEPS = [
  "GATE Details",
  "Personal Details",
  "Branch Preferences",
  "Location",
  "Constraints",
  "Academic Background",
];

const CATEGORIES = ["UR", "OBC", "SC", "ST", "EWS"];

const FALLBACK_BRANCHES = [
  { code: "CSE", name: "Computer Science & Engineering" },
];

const REGIONS = [
  "East India",
  "West India",
  "North India",
  "South India",
  "Any",
];

export default function Profile() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [homeNIT, setHomeNIT] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [branchList, setBranchList] = useState(FALLBACK_BRANCHES);

  // CV state — all variables properly declared
  const [cvUploading, setCvUploading] = useState(false);
  const [cvExtracted, setCvExtracted] = useState(false);
  const [cvConfirmed, setCvConfirmed] = useState(false);
  const [cvSaved, setCvSaved] = useState(false);
  const [cvError, setCvError] = useState("");
  const [manualBranch, setManualBranch] = useState("");
  const [manualCGPA, setManualCGPA] = useState("");
  const [useInRecommendations, setUseInRecommendations] = useState(true);
  const [cvCgpaNote, setCvCgpaNote] = useState("");

  const [gate, setGate] = useState({
    gate_score: "",
    gate_year: 2026,
    gate_air: "",
    category: "OBC",
  });

  const [personal, setPersonal] = useState({
    gender: "Male",
    pwd_status: false,
    domicile_state: "",
  });

  const [branches, setBranches] = useState({
    priorities: ["CSE"],
    any_branch: false,
    strict_filter: false,
  });

  const [location, setLocation] = useState({
    preferred_region: "Any",
    states_to_avoid: [],
  });

  const [constraints, setConstraints] = useState({
    risk_appetite: "Moderate",
    mtech_goal: "Industry",
    fee_budget: 150000,
    hostel_needed: true,
    has_backlogs: false,
    btec_cgpa: "",
  });

  // Load branch list from backend
  useEffect(() => {
    fetch("http://localhost:8000/api/v1/nits")
      .then((r) => r.json())
      .then((data) => {
        const branchSet = new Map();
        (data.nits || []).forEach((n) => {
          (n.mtech_programs || []).forEach((p) => {
            branchSet.set(p.short_name, p.short_name_full || p.short_name);
          });
        });
        const dynamicBranches = Array.from(branchSet, ([code, name]) => ({
          code,
          name,
        })).sort((a, b) => a.code.localeCompare(b.code));
        if (dynamicBranches.length > 0) setBranchList(dynamicBranches);
      })
      .catch((err) => console.error("Could not load branch list", err));
  }, []);

  // Load existing profile
  useEffect(() => {
    loadExistingProfile();
  }, []);

  const loadExistingProfile = async () => {
    try {
      const res = await getProfile(token);
      const p = res.data;

      if (p.profile_complete) setIsEditing(true);

      if (p.gate_score)
        setGate({
          gate_score: p.gate_score ?? "",
          gate_year: p.gate_year ?? 2026,
          gate_air: p.gate_air ?? "",
          category: p.category ?? "OBC",
        });

      if (p.gender)
        setPersonal({
          gender: p.gender ?? "Male",
          pwd_status: p.pwd_status ?? false,
          domicile_state: p.domicile_state ?? "",
        });

      if (p.branch_priorities)
        setBranches({
          priorities: p.branch_priorities ?? ["CSE"],
          any_branch: p.any_branch ?? false,
          strict_filter: p.strict_filter ?? false,
        });

      if (p.preferred_region)
        setLocation({
          preferred_region: p.preferred_region ?? "Any",
          states_to_avoid: p.states_to_avoid ?? [],
        });

      if (p.risk_appetite)
        setConstraints({
          risk_appetite: p.risk_appetite ?? "Moderate",
          mtech_goal: p.mtech_goal ?? "Industry",
          fee_budget: p.fee_budget ?? 150000,
          hostel_needed: p.hostel_needed ?? true,
          has_backlogs: p.has_backlogs ?? false,
          btec_cgpa: p.btec_cgpa ?? "",
        });

      if (p.home_state_nit) setHomeNIT(p.home_state_nit);

      // Pre-fill CV if already saved
      if (p.btech_branch) {
        setManualBranch(p.btech_branch);
        setCvConfirmed(true);
        setCvSaved(true);
      }
      if (p.btech_cgpa) {
        setManualCGPA(String(p.btech_cgpa));
      }
      if (typeof p.use_cv_in_recommendations === "boolean") {
        setUseInRecommendations(p.use_cv_in_recommendations);
      }
    } catch (err) {
      console.error("Could not load profile", err);
    } finally {
      setFetching(false);
    }
  };

  const toggleBranch = (branchCode) => {
    setBranches((prev) => ({
      ...prev,
      priorities: prev.priorities.includes(branchCode)
        ? prev.priorities.filter((b) => b !== branchCode)
        : [...prev.priorities, branchCode],
    }));
  };

  // CV: upload and extract (does NOT save to DB)
  const handleCVUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setCvUploading(true);
    setCvError("");
    setCvExtracted(false);
    setCvConfirmed(false);
    setCvSaved(false);
    try {
      const res = await uploadCV(token, file);
      if (res.data.extraction_success) {
        setManualBranch(res.data.btech_branch || "");
        setManualCGPA(res.data.btech_cgpa ? String(res.data.btech_cgpa) : "");
        setCvExtracted(true);
        setCvCgpaNote(res.data.cgpa_note || "");
      } else {
        setCvError(
          res.data.error ||
            "Could not extract automatically. Please fill in manually.",
        );
      }
    } catch (err) {
      setCvError("Upload failed. Check the file is a valid PDF and try again.");
    } finally {
      setCvUploading(false);
    }
  };

  // CV: save confirmed data to DB
  const handleSaveCV = async () => {
    if (!manualBranch) {
      setCvError("Please select your B.Tech branch.");
      return;
    }
    if (!cvConfirmed) {
      setCvError("Please confirm the details are yours.");
      return;
    }
    setCvError("");
    try {
      await confirmCV(
        token,
        manualBranch,
        parseFloat(manualCGPA) || 8.0,
        true,
        useInRecommendations,
      );
      setCvSaved(true);
    } catch (err) {
      setCvError(err.response?.data?.detail || "Could not save. Try again.");
    }
  };

  // Step navigation
  const handleNext = async () => {
    setLoading(true);
    setError("");

    try {
      if (step === 0) {
        await saveGATEDetails(
          {
            gate_score: parseFloat(gate.gate_score),
            gate_year: gate.gate_year,
            gate_air: gate.gate_air ? parseInt(gate.gate_air) : null,
            category: gate.category,
          },
          token,
        );
      }

      if (step === 1) {
        const res = await savePersonalDetails(personal, token);
        if (res.data.home_state_advantage) {
          const nit = res.data.home_state_advantage.split(": ")[1];
          setHomeNIT(nit);
          setLoading(false);
          setStep(step + 1);
          return;
        }
      }

      if (step === 2) await saveBranchPreferences(branches, token);
      if (step === 3) await saveLocationPreferences(location, token);

      if (step === 4) {
        await saveConstraints(
          {
            ...constraints,
            btec_cgpa: constraints.btec_cgpa
              ? parseFloat(constraints.btec_cgpa)
              : null,
            fee_budget: parseInt(constraints.fee_budget),
          },
          token,
        );
        setLoading(false);
        setStep(step + 1);
        return;
      }

      // Step 5 (CV) — just navigate, CV is saved via its own button
      if (step === 5) {
        navigate("/dashboard");
        return;
      }

      setStep(step + 1);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Something went wrong. Try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-blue-900 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Loading your profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-blue-900 mb-1">
            {isEditing ? "Edit Your Profile" : "Complete Your Profile"}
          </h1>
          <p className="text-gray-400 text-sm">
            Step {step + 1} of {STEPS.length} — {STEPS[step]}
          </p>
          {isEditing && (
            <p className="text-xs text-green-600 mt-1">
              ✅ Your existing data is pre-filled — just change what you need
            </p>
          )}
        </div>

        {/* Progress bar */}
        <div className="flex gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div
              key={i}
              onClick={() => i < step && setStep(i)}
              className={`h-1.5 flex-1 rounded-full transition-all ${
                i <= step ? "bg-blue-900" : "bg-gray-200"
              } ${i < step ? "cursor-pointer hover:bg-blue-700" : ""}`}
            />
          ))}
        </div>

        {/* Step tabs (editing mode only) */}
        {isEditing && (
          <div className="flex gap-1 mb-6 flex-wrap">
            {STEPS.map((s, i) => (
              <button
                key={i}
                onClick={() => setStep(i)}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
                  step === i
                    ? "bg-blue-900 text-white"
                    : "bg-white text-gray-500 border border-gray-200 hover:border-blue-300"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          {/* ── Step 0: GATE Details ── */}
          {step === 0 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Your GATE Details
              </h2>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  GATE Score (out of 1000)
                </label>
                <input
                  type="number"
                  value={gate.gate_score}
                  onChange={(e) =>
                    setGate({ ...gate, gate_score: e.target.value })
                  }
                  placeholder="e.g. 615"
                  min="0"
                  max="1000"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  GATE Year
                </label>
                <input
                  type="number"
                  value={gate.gate_year}
                  onChange={(e) =>
                    setGate({ ...gate, gate_year: parseInt(e.target.value) })
                  }
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  GATE AIR{" "}
                  <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="number"
                  value={gate.gate_air}
                  onChange={(e) =>
                    setGate({ ...gate, gate_air: e.target.value })
                  }
                  placeholder="e.g. 4200"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Category
                </label>
                <div className="flex gap-2 flex-wrap">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setGate({ ...gate, category: cat })}
                      className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all ${
                        gate.category === cat
                          ? "bg-blue-900 text-white border-blue-900"
                          : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Step 1: Personal ── */}
          {step === 1 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Personal Details
              </h2>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Gender
                </label>
                <div className="flex gap-3">
                  {["Male", "Female", "Other"].map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setPersonal({ ...personal, gender: g })}
                      className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        personal.gender === g
                          ? "bg-blue-900 text-white border-blue-900"
                          : "bg-white text-gray-600 border-gray-200"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  Domicile State
                </label>
                <select
                  value={personal.domicile_state}
                  onChange={(e) => {
                    const state = e.target.value;
                    setPersonal({ ...personal, domicile_state: state });
                    const mapping = {
                      "Andhra Pradesh": "NIT Andhra Pradesh",
                      Assam: "NIT Silchar",
                      Bihar: "NIT Patna",
                      Chhattisgarh: "NIT Raipur",
                      Delhi: "NIT Delhi",
                      Goa: "NIT Goa",
                      Gujarat: "NIT Surat",
                      Haryana: "NIT Kurukshetra",
                      "Himachal Pradesh": "NIT Hamirpur",
                      Jharkhand: "NIT Jamshedpur",
                      Karnataka: "NIT Surathkal",
                      Kerala: "NIT Calicut",
                      "Madhya Pradesh": "NIT Bhopal",
                      Maharashtra: "NIT Nagpur",
                      Manipur: "NIT Manipur",
                      Meghalaya: "NIT Meghalaya",
                      Mizoram: "NIT Mizoram",
                      Nagaland: "NIT Nagaland",
                      Odisha: "NIT Rourkela",
                      Punjab: "NIT Jalandhar",
                      Rajasthan: "NIT Jaipur",
                      Sikkim: "NIT Sikkim",
                      "Tamil Nadu": "NIT Trichy",
                      Telangana: "NIT Warangal",
                      Tripura: "NIT Agartala",
                      "Uttar Pradesh": "NIT Allahabad",
                      Uttarakhand: "NIT Uttarakhand",
                      "West Bengal": "NIT Durgapur",
                    };
                    setHomeNIT(mapping[state] || "");
                  }}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400 bg-white"
                >
                  <option value="">Select your state</option>
                  {[
                    "Andhra Pradesh",
                    "Assam",
                    "Bihar",
                    "Chhattisgarh",
                    "Delhi",
                    "Goa",
                    "Gujarat",
                    "Haryana",
                    "Himachal Pradesh",
                    "Jharkhand",
                    "Karnataka",
                    "Kerala",
                    "Madhya Pradesh",
                    "Maharashtra",
                    "Manipur",
                    "Meghalaya",
                    "Mizoram",
                    "Nagaland",
                    "Odisha",
                    "Punjab",
                    "Rajasthan",
                    "Sikkim",
                    "Tamil Nadu",
                    "Telangana",
                    "Tripura",
                    "Uttar Pradesh",
                    "Uttarakhand",
                    "West Bengal",
                  ].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="pwd"
                  checked={personal.pwd_status}
                  onChange={(e) =>
                    setPersonal({ ...personal, pwd_status: e.target.checked })
                  }
                  className="w-4 h-4 accent-blue-900"
                />
                <label htmlFor="pwd" className="text-sm text-gray-700">
                  Person with Disability (PwD)
                </label>
              </div>
              {homeNIT && (
                <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-3 text-green-700 text-sm">
                  🏠 Home state NIT — <strong>{homeNIT}</strong>
                </div>
              )}
            </div>
          )}

          {/* ── Step 2: Branch ── */}
          {step === 2 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Branch Preferences
              </h2>
              <p className="text-sm text-gray-400">
                Select all branches you want. First selected = highest priority.
              </p>
              <div className="flex gap-2 flex-wrap">
                {branchList.map((branch) => (
                  <button
                    key={branch.code}
                    type="button"
                    onClick={() => toggleBranch(branch.code)}
                    className={`px-3 py-2 rounded-xl border text-xs font-medium transition-all text-left ${
                      branches.priorities.includes(branch.code)
                        ? "bg-blue-900 text-white border-blue-900"
                        : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                    }`}
                  >
                    <span className="block font-semibold">{branch.code}</span>
                    <span className="block text-xs opacity-75">
                      {branch.name}
                    </span>
                  </button>
                ))}
              </div>
              {branches.priorities.length > 0 && (
                <div className="bg-blue-50 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-blue-400 font-medium">
                      Your priority order:
                    </p>
                    <button
                      type="button"
                      onClick={() =>
                        setBranches({ ...branches, priorities: [] })
                      }
                      className="text-xs text-red-500 hover:text-red-700 font-medium"
                    >
                      Reset all
                    </button>
                  </div>
                  {branches.priorities.map((b, i) => {
                    const found = branchList.find((br) => br.code === b);
                    return (
                      <p key={b} className="text-sm text-blue-800">
                        {i + 1}. {b} —{" "}
                        {found ? found.name : `${b} (invalid — click Reset)`}
                      </p>
                    );
                  })}
                </div>
              )}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="any"
                  checked={branches.any_branch}
                  onChange={(e) =>
                    setBranches({ ...branches, any_branch: e.target.checked })
                  }
                  className="w-4 h-4 accent-blue-900"
                />
                <label htmlFor="any" className="text-sm text-gray-700">
                  Any branch is fine
                </label>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="strict"
                    checked={branches.strict_filter}
                    onChange={(e) =>
                      setBranches({
                        ...branches,
                        strict_filter: e.target.checked,
                      })
                    }
                    className="w-4 h-4 accent-blue-900 mt-0.5"
                  />
                  <label htmlFor="strict" className="text-sm text-gray-700">
                    <span className="font-medium block mb-1">
                      Only show branches I selected above
                    </span>
                    <span className="text-xs text-gray-500">
                      If unchecked, all branches are shown and ranked by your
                      preference. If checked, only your selected branches appear
                      in recommendations and choice filing.
                    </span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* ── Step 3: Location ── */}
          {step === 3 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Location Preferences
              </h2>
              <div className="flex flex-col gap-2">
                {REGIONS.map((region) => (
                  <button
                    key={region}
                    type="button"
                    onClick={() =>
                      setLocation({ ...location, preferred_region: region })
                    }
                    className={`w-full py-2.5 rounded-xl border text-sm font-medium text-left px-4 transition-all ${
                      location.preferred_region === region
                        ? "bg-blue-900 text-white border-blue-900"
                        : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                    }`}
                  >
                    {region}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Step 4: Constraints ── */}
          {step === 4 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Other Preferences
              </h2>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  Risk Appetite
                </label>
                <div className="flex gap-2">
                  {["Safe", "Moderate", "Ambitious"].map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() =>
                        setConstraints({ ...constraints, risk_appetite: r })
                      }
                      className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        constraints.risk_appetite === r
                          ? "bg-blue-900 text-white border-blue-900"
                          : "bg-white text-gray-600 border-gray-200"
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">
                  M.Tech Goal
                </label>
                <div className="flex gap-2">
                  {["Industry", "Research", "Undecided"].map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() =>
                        setConstraints({ ...constraints, mtech_goal: g })
                      }
                      className={`flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        constraints.mtech_goal === g
                          ? "bg-blue-900 text-white border-blue-900"
                          : "bg-white text-gray-600 border-gray-200"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  Fee Budget (per year in Rs)
                </label>
                <input
                  type="number"
                  value={constraints.fee_budget}
                  onChange={(e) =>
                    setConstraints({
                      ...constraints,
                      fee_budget: e.target.value,
                    })
                  }
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  B.Tech CGPA{" "}
                  <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  type="number"
                  value={constraints.btec_cgpa}
                  onChange={(e) =>
                    setConstraints({
                      ...constraints,
                      btec_cgpa: e.target.value,
                    })
                  }
                  placeholder="e.g. 7.8"
                  step="0.1"
                  min="0"
                  max="10"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="hostel"
                    checked={constraints.hostel_needed}
                    onChange={(e) =>
                      setConstraints({
                        ...constraints,
                        hostel_needed: e.target.checked,
                      })
                    }
                    className="w-4 h-4 accent-blue-900"
                  />
                  <label htmlFor="hostel" className="text-sm text-gray-700">
                    Hostel required
                  </label>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="backlogs"
                    checked={constraints.has_backlogs}
                    onChange={(e) =>
                      setConstraints({
                        ...constraints,
                        has_backlogs: e.target.checked,
                      })
                    }
                    className="w-4 h-4 accent-blue-900"
                  />
                  <label htmlFor="backlogs" className="text-sm text-gray-700">
                    I have active backlogs
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* ── Step 5: Academic Background (CV) ── */}
          {step === 5 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="font-semibold text-gray-800 mb-1">
                  Academic Background
                </h2>
                <p className="text-sm text-gray-400">
                  Optional. Adds a small bonus on top of the core 5-factor
                  recommendation system. The 5 factors are unchanged.
                </p>
              </div>

              {/* CV Upload area */}
              <div>
                <p className="text-xs font-medium text-gray-600 mb-2">
                  Upload your CV (PDF) to auto-detect branch and CGPA:
                </p>
                <label
                  htmlFor="cv-upload"
                  className="flex flex-col items-center justify-center border-2 border-dashed border-gray-200 rounded-xl p-5 cursor-pointer hover:border-blue-300 transition-all bg-gray-50"
                >
                  <input
                    type="file"
                    id="cv-upload"
                    accept=".pdf"
                    onChange={handleCVUpload}
                    className="hidden"
                  />
                  {cvUploading ? (
                    <div className="flex items-center gap-2 text-blue-700">
                      <div className="w-4 h-4 border-2 border-blue-700 border-t-transparent rounded-full animate-spin" />
                      <span className="text-sm">Extracting from CV...</span>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm font-medium text-blue-700">
                        Click to upload CV (PDF, max 5MB)
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        Only B.Tech branch and CGPA are read. Your CV file is
                        not stored.
                      </p>
                    </>
                  )}
                </label>

                {/* Extraction result banner */}
                {cvExtracted && (
                  <div className="mt-2 bg-blue-50 border border-blue-200 rounded-xl px-4 py-2.5">
                    <p className="text-xs text-blue-700 font-medium">
                      ✓ Extracted from CV — please verify and confirm below
                    </p>
                    {cvCgpaNote && (
                      <p className="text-xs text-amber-600 mt-1">
                        ⚠️ {cvCgpaNote}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-gray-100" />
                <span className="text-xs text-gray-400">
                  {cvExtracted ? "verify or edit" : "fill manually"}
                </span>
                <div className="flex-1 h-px bg-gray-100" />
              </div>

              {/* Manual / editable fields */}
              <div className="flex flex-col gap-3">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    B.Tech Branch
                  </label>
                  <select
                    value={manualBranch}
                    onChange={(e) => {
                      setManualBranch(e.target.value);
                      setCvSaved(false);
                    }}
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
                  >
                    <option value="">Select your branch</option>
                    <option value="CS_IT">
                      CS / IT / Software Engineering
                    </option>
                    <option value="ECE_EE">ECE / EE / Electronics</option>
                    <option value="MECHANICAL">Mechanical / Production</option>
                    <option value="CIVIL">Civil / Environmental</option>
                    <option value="CHEMICAL">Chemical Engineering</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    B.Tech CGPA
                  </label>
                  <input
                    type="number"
                    value={manualCGPA}
                    onChange={(e) => {
                      setManualCGPA(e.target.value);
                      setCvSaved(false);
                    }}
                    placeholder="e.g. 8.5"
                    step="0.1"
                    min="0"
                    max="10"
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                </div>

                {/* Confirmation checkbox — shown when branch is selected */}
                {manualBranch && (
                  <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-3">
                    <input
                      type="checkbox"
                      id="cv-confirm"
                      checked={cvConfirmed}
                      onChange={(e) => {
                        setCvConfirmed(e.target.checked);
                        setCvSaved(false);
                      }}
                      className="w-4 h-4 accent-blue-900 mt-0.5"
                    />
                    <label
                      htmlFor="cv-confirm"
                      className="text-xs text-gray-700"
                    >
                      I confirm this is my own academic information and it is
                      accurate to the best of my knowledge.
                    </label>
                  </div>
                )}

                {/* Toggle — shown when confirmed */}
                {cvConfirmed && (
                  <div className="flex items-center justify-between bg-blue-50 rounded-xl px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-800">
                        Include in recommendations
                      </p>
                      <p className="text-xs text-gray-500">
                        Adds small bonus. Core 5-factor system unchanged.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setUseInRecommendations((p) => !p);
                        setCvSaved(false);
                      }}
                      className={`w-11 h-6 rounded-full transition-all relative flex items-center ${
                        useInRecommendations ? "bg-blue-900" : "bg-gray-300"
                      }`}
                    >
                      <span
                        className={`w-4 h-4 bg-white rounded-full absolute transition-all shadow ${
                          useInRecommendations ? "left-6" : "left-1"
                        }`}
                      />
                    </button>
                  </div>
                )}

                {/* Save button */}
                <button
                  type="button"
                  onClick={handleSaveCV}
                  disabled={!manualBranch || !cvConfirmed}
                  className="w-full py-2.5 rounded-xl bg-blue-900 text-white text-sm font-medium disabled:opacity-40 hover:bg-blue-800 transition-all"
                >
                  Save background details
                </button>

                {/* Saved confirmation */}
                {cvSaved && (
                  <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-2.5">
                    <p className="text-xs text-green-700 font-medium">
                      ✓ Saved — {manualBranch} ·{" "}
                      {manualCGPA ? `CGPA ${manualCGPA} · ` : ""}
                      {useInRecommendations
                        ? "Included in recommendations"
                        : "Not included in recommendations"}
                    </p>
                  </div>
                )}

                {cvError && <p className="text-red-500 text-sm">{cvError}</p>}
              </div>

              {/* How it works */}
              <div className="bg-gray-50 rounded-xl p-3 text-xs text-gray-500">
                <p className="font-medium text-gray-700 mb-1">
                  How this bonus works:
                </p>
                <p>CS/IT background + CSE/AI/DS programme → +3 pts</p>
                <p>ECE/EE background → neutral</p>
                <p>CGPA ≥ 8.5 → +2 pts · CGPA &lt; 7.0 → −2 pts</p>
                <p className="mt-1 text-gray-400">
                  The 5-factor system (probability, NIRF, sentiment, location,
                  branch priority) is completely unchanged. This is a small
                  optional add-on shown separately.
                </p>
              </div>

              {/* Skip */}
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="text-xs text-gray-400 hover:text-gray-600 text-center"
              >
                Skip — go to dashboard without saving
              </button>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-red-600 text-sm mt-4">
              {error}
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex gap-3 mt-6">
            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="flex-1 py-2.5 rounded-xl border border-gray-200 text-gray-600 text-sm font-medium hover:bg-gray-50"
              >
                Back
              </button>
            )}
            <button
              type="button"
              onClick={handleNext}
              disabled={loading}
              className="flex-1 bg-blue-900 text-white font-semibold py-2.5 rounded-xl hover:bg-blue-800 disabled:opacity-50 text-sm"
            >
              {loading
                ? "Saving..."
                : step === STEPS.length - 1
                  ? isEditing
                    ? "Save Changes"
                    : "Go to Dashboard"
                  : "Next"}
            </button>
          </div>
        </div>

        {isEditing && (
          <button
            onClick={() => navigate("/profile-view")}
            className="w-full text-gray-400 text-sm mt-4 hover:text-gray-600"
          >
            Cancel — go back to profile
          </button>
        )}
      </div>
    </div>
  );
}
