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
  setCVManual,
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

  // CV state
  const [cvUploading, setCvUploading]   = useState(false);
  const [cvResult, setCvResult]         = useState(null);
  const [cvError, setCvError]           = useState("");
  const [manualBranch, setManualBranch] = useState("");
  const [manualCGPA, setManualCGPA]     = useState("");

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
        const dynamicBranches = Array.from(
          branchSet,
          ([code, name]) => ({ code, name })
        ).sort((a, b) => a.code.localeCompare(b.code));
        if (dynamicBranches.length > 0) setBranchList(dynamicBranches);
      })
      .catch((err) =>
        console.error("Could not load branch list, using fallback", err)
      );
  }, []);

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

      // Pre-fill CV fields if already extracted
      if (p.btech_branch || p.btech_cgpa) {
        setCvResult({
          btech_branch: p.btech_branch,
          btech_cgpa:   p.btech_cgpa,
        });
        setManualBranch(p.btech_branch || "");
        setManualCGPA(p.btech_cgpa ? String(p.btech_cgpa) : "");
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

  // CV handlers
  const handleCVUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setCvUploading(true);
    setCvError("");
    setCvResult(null);
    try {
      const res = await uploadCV(token, file);
      setCvResult(res.data);
      if (res.data.btech_branch)
        setManualBranch(res.data.btech_branch);
      if (res.data.btech_cgpa)
        setManualCGPA(String(res.data.btech_cgpa));
    } catch (err) {
      setCvError("CV upload failed. Please fill in manually.");
    } finally {
      setCvUploading(false);
    }
  };

  const handleManualCV = async () => {
    if (!manualBranch) {
      setCvError("Please select your B.Tech branch.");
      return;
    }
    setCvError("");
    try {
      await setCVManual(
        token,
        manualBranch,
        parseFloat(manualCGPA) || 8.0
      );
      setCvResult({
        btech_branch: manualBranch,
        btech_cgpa:   parseFloat(manualCGPA) || 8.0,
      });
    } catch (err) {
      setCvError("Could not save. Try again.");
    }
  };

  const handleNext = async () => {
    setLoading(true);
    setError("");

    try {
      if (step === 0) {
        await saveGATEDetails(
          {
            gate_score: parseFloat(gate.gate_score),
            gate_year:  gate.gate_year,
            gate_air:   gate.gate_air ? parseInt(gate.gate_air) : null,
            category:   gate.category,
          },
          token
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
            btec_cgpa:  constraints.btec_cgpa
              ? parseFloat(constraints.btec_cgpa)
              : null,
            fee_budget: parseInt(constraints.fee_budget),
          },
          token
        );
        // Move to Step 6 (CV) instead of navigating away
        setStep(step + 1);
        setLoading(false);
        return;
      }

      // Step 5 (CV) — save if manual entry filled, then go to dashboard
      if (step === 5) {
        if (manualBranch && !cvResult) {
          await setCVManual(
            token,
            manualBranch,
            parseFloat(manualCGPA) || 8.0
          );
        }
        navigate("/dashboard");
        return;
      }

      setStep(step + 1);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Something went wrong. Try again."
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

        {/* Step tabs */}
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

          {/* Step 0: GATE Details */}
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
                  onChange={(e) => setGate({ ...gate, gate_score: e.target.value })}
                  placeholder="e.g. 615"
                  min="0" max="1000"
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
                  onChange={(e) => setGate({ ...gate, gate_year: parseInt(e.target.value) })}
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
                  onChange={(e) => setGate({ ...gate, gate_air: e.target.value })}
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
                      key={cat} type="button"
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

          {/* Step 1: Personal */}
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
                      key={g} type="button"
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
                    "Andhra Pradesh","Assam","Bihar","Chhattisgarh",
                    "Delhi","Goa","Gujarat","Haryana","Himachal Pradesh",
                    "Jharkhand","Karnataka","Kerala","Madhya Pradesh",
                    "Maharashtra","Manipur","Meghalaya","Mizoram",
                    "Nagaland","Odisha","Punjab","Rajasthan","Sikkim",
                    "Tamil Nadu","Telangana","Tripura","Uttar Pradesh",
                    "Uttarakhand","West Bengal",
                  ].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox" id="pwd"
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

          {/* Step 2: Branch */}
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
                    key={branch.code} type="button"
                    onClick={() => toggleBranch(branch.code)}
                    className={`px-3 py-2 rounded-xl border text-xs font-medium transition-all text-left ${
                      branches.priorities.includes(branch.code)
                        ? "bg-blue-900 text-white border-blue-900"
                        : "bg-white text-gray-600 border-gray-200 hover:border-blue-300"
                    }`}
                  >
                    <span className="block font-semibold">{branch.code}</span>
                    <span className="block text-xs opacity-75">{branch.name}</span>
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
                      onClick={() => setBranches({ ...branches, priorities: [] })}
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
                  type="checkbox" id="any"
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
                    type="checkbox" id="strict"
                    checked={branches.strict_filter}
                    onChange={(e) =>
                      setBranches({ ...branches, strict_filter: e.target.checked })
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

          {/* Step 3: Location */}
          {step === 3 && (
            <div className="flex flex-col gap-4">
              <h2 className="font-semibold text-gray-800 mb-2">
                Location Preferences
              </h2>
              <div className="flex flex-col gap-2">
                {REGIONS.map((region) => (
                  <button
                    key={region} type="button"
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

          {/* Step 4: Constraints */}
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
                      key={r} type="button"
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
                      key={g} type="button"
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
                    setConstraints({ ...constraints, fee_budget: e.target.value })
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
                    setConstraints({ ...constraints, btec_cgpa: e.target.value })
                  }
                  placeholder="e.g. 7.8"
                  step="0.1" min="0" max="10"
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox" id="hostel"
                    checked={constraints.hostel_needed}
                    onChange={(e) =>
                      setConstraints({
                        ...constraints, hostel_needed: e.target.checked,
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
                    type="checkbox" id="backlogs"
                    checked={constraints.has_backlogs}
                    onChange={(e) =>
                      setConstraints({
                        ...constraints, has_backlogs: e.target.checked,
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

          {/* Step 5: Academic Background (CV) */}
          {step === 5 && (
            <div className="flex flex-col gap-5">
              <div>
                <h2 className="font-semibold text-gray-800 mb-1">
                  Academic Background
                </h2>
                <p className="text-sm text-gray-400">
                  Optional — helps personalise your NIT recommendations
                  based on your B.Tech background.
                </p>
              </div>

              {/* CV Upload */}
              <div>
                <p className="text-xs font-medium text-gray-600 mb-2">
                  Upload your CV (PDF) to auto-detect:
                </p>
                <label
                  htmlFor="cv-upload"
                  className="flex flex-col items-center justify-center border-2 border-dashed border-gray-200 rounded-xl p-6 cursor-pointer hover:border-blue-300 transition-all bg-gray-50"
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
                        Only B.Tech branch and CGPA are extracted.
                        Your CV is not stored.
                      </p>
                    </>
                  )}
                </label>

                {/* Extraction result */}
                {cvResult && cvResult.extraction_success && (
                  <div className="mt-3 bg-green-50 border border-green-200 rounded-xl px-4 py-3">
                    <p className="text-xs font-medium text-green-700 mb-1">
                      ✓ Extracted from CV
                    </p>
                    <p className="text-sm text-gray-700">
                      B.Tech Branch:{" "}
                      <strong>{cvResult.btech_branch}</strong>
                    </p>
                    <p className="text-sm text-gray-700">
                      CGPA: <strong>{cvResult.btech_cgpa}</strong>
                    </p>
                  </div>
                )}
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-gray-100" />
                <span className="text-xs text-gray-400">
                  or fill in manually
                </span>
                <div className="flex-1 h-px bg-gray-100" />
              </div>

              {/* Manual entry */}
              <div className="flex flex-col gap-3">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    B.Tech Branch
                  </label>
                  <select
                    value={manualBranch}
                    onChange={(e) => setManualBranch(e.target.value)}
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-white focus:outline-none focus:border-blue-400"
                  >
                    <option value="">Select your branch</option>
                    <option value="CS_IT">CS / IT / Software Engineering</option>
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
                    onChange={(e) => setManualCGPA(e.target.value)}
                    placeholder="e.g. 8.5"
                    step="0.1" min="0" max="10"
                    className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                </div>

                <button
                  type="button"
                  onClick={handleManualCV}
                  className="w-full py-2.5 rounded-xl border border-blue-300 text-blue-800 text-sm font-medium hover:bg-blue-50"
                >
                  Save background details
                </button>

                {cvResult && !cvResult.extraction_success &&
                 cvResult.btech_branch && (
                  <div className="bg-green-50 border border-green-200 rounded-xl px-4 py-2.5">
                    <p className="text-xs text-green-700 font-medium">
                      ✓ Saved manually
                    </p>
                    <p className="text-sm text-gray-700">
                      Branch: <strong>{cvResult.btech_branch}</strong>
                      {cvResult.btech_cgpa && (
                        <> · CGPA: <strong>{cvResult.btech_cgpa}</strong></>
                      )}
                    </p>
                  </div>
                )}
              </div>

              {/* Score impact explanation */}
              <div className="bg-blue-50 rounded-xl p-3">
                <p className="text-xs font-medium text-blue-800 mb-1">
                  How this affects your recommendations
                </p>
                <p className="text-xs text-blue-700">
                  CS/IT background + CSE/AI/DS programmes → small bonus<br />
                  ECE/EE background → neutral<br />
                  Other branches → small adjustment<br />
                  CGPA ≥ 8.5 → small bonus · CGPA &lt; 7.0 → small penalty
                </p>
              </div>

              {cvError && (
                <p className="text-red-500 text-sm">{cvError}</p>
              )}

              {/* Skip option */}
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="text-xs text-gray-400 hover:text-gray-600 text-center"
              >
                Skip this step — go to dashboard
              </button>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-red-600 text-sm mt-4">
              {error}
            </div>
          )}

          {/* Navigation */}
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
                  : "Complete Profile"
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