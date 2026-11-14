/** Citizen-facing strings. Safety instructions come from the reviewed server templates. */

export type Lang = "en" | "hi" | "as" | "bn" | "ne";

export const LANGUAGES: Array<{ code: Lang; label: string; reviewed: boolean }> = [
  { code: "en", label: "English", reviewed: true },
  { code: "hi", label: "हिन्दी", reviewed: false },
  { code: "as", label: "অসমীয়া", reviewed: false },
  { code: "bn", label: "বাংলা", reviewed: false },
  { code: "ne", label: "नेपाली", reviewed: false },
];

type Dict = {
  title: string;
  subtitle: string;
  useLocation: string;
  chooseDistrict: string;
  check: string;
  checking: string;
  riskHere: string;
  officialAdvisory: string;
  noAdvisory: string;
  updated: string;
  safety: string;
  reportHazard: string;
  hazardType: string;
  describe: string;
  addPhoto: string;
  consent: string;
  submit: string;
  submitting: string;
  submitted: string;
  pending: string;
  disclaimer: string;
  emergency: string;
};

const strings: Record<Lang, Dict> = {
  en: {
    title: "Is my area safe?",
    subtitle: "Check landslide conditions for a location in the pilot districts.",
    useLocation: "Use my location",
    chooseDistrict: "Or choose a district centre",
    check: "Check this area",
    checking: "Checking…",
    riskHere: "Current landslide risk",
    officialAdvisory: "Official advisory",
    noAdvisory: "No official advisory is active for this area.",
    updated: "Last updated",
    safety: "What to do",
    reportHazard: "Report a hazard",
    hazardType: "What did you see?",
    describe: "Describe it briefly",
    addPhoto: "Add a photo (optional)",
    consent: "I consent to sharing this location and photo with the district authority.",
    submit: "Send report",
    submitting: "Sending…",
    submitted: "Report received. It is pending verification by an officer.",
    pending: "Pending verification",
    disclaimer: "Decision support only — not an official warning.",
    emergency: "Emergency: call 112",
  },
  hi: {
    title: "क्या मेरा क्षेत्र सुरक्षित है?",
    subtitle: "पायलट जिलों में किसी स्थान के भूस्खलन की स्थिति देखें।",
    useLocation: "मेरा स्थान उपयोग करें",
    chooseDistrict: "या जिला केंद्र चुनें",
    check: "इस क्षेत्र की जाँच करें",
    checking: "जाँच हो रही है…",
    riskHere: "वर्तमान भूस्खलन जोखिम",
    officialAdvisory: "आधिकारिक चेतावनी",
    noAdvisory: "इस क्षेत्र के लिए कोई आधिकारिक चेतावनी सक्रिय नहीं है।",
    updated: "अंतिम अद्यतन",
    safety: "क्या करें",
    reportHazard: "खतरा रिपोर्ट करें",
    hazardType: "आपने क्या देखा?",
    describe: "संक्षेप में बताएं",
    addPhoto: "फ़ोटो जोड़ें (वैकल्पिक)",
    consent: "मैं इस स्थान और फ़ोटो को जिला प्रशासन के साथ साझा करने की सहमति देता/देती हूँ।",
    submit: "रिपोर्ट भेजें",
    submitting: "भेजा जा रहा है…",
    submitted: "रिपोर्ट प्राप्त हुई। अधिकारी द्वारा सत्यापन लंबित है।",
    pending: "सत्यापन लंबित",
    disclaimer: "केवल निर्णय सहायता — आधिकारिक चेतावनी नहीं।",
    emergency: "आपातकाल: 112 पर कॉल करें",
  },
  as: {
    title: "মোৰ অঞ্চল সুৰক্ষিত নেকি?",
    subtitle: "পাইলট জিলাত কোনো স্থানৰ ভূমিস্খলন পৰিস্থিতি চাওক।",
    useLocation: "মোৰ স্থান ব্যৱহাৰ কৰক",
    chooseDistrict: "বা জিলা কেন্দ্ৰ বাছনি কৰক",
    check: "এই অঞ্চল পৰীক্ষা কৰক",
    checking: "পৰীক্ষা চলি আছে…",
    riskHere: "বৰ্তমান ভূমিস্খলন বিপদ",
    officialAdvisory: "চৰকাৰী সতৰ্কবাণী",
    noAdvisory: "এই অঞ্চলৰ বাবে কোনো চৰকাৰী সতৰ্কবাণী সক্ৰিয় নহয়।",
    updated: "শেষ আপডেট",
    safety: "কি কৰিব",
    reportHazard: "বিপদ জনাওক",
    hazardType: "আপুনি কি দেখিলে?",
    describe: "চমুকৈ বৰ্ণনা কৰক",
    addPhoto: "ফটো যোগ কৰক (ঐচ্ছিক)",
    consent: "এই স্থান আৰু ফটো জিলা প্ৰশাসনৰ সৈতে ভাগ কৰিবলৈ মই সন্মতি দিওঁ।",
    submit: "ৰিপৰ্ট পঠিয়াওক",
    submitting: "পঠিয়াই আছে…",
    submitted: "ৰিপৰ্ট পোৱা গৈছে। বিষয়াৰ সত্যাপন বাকী আছে।",
    pending: "সত্যাপন বাকী",
    disclaimer: "কেৱল সিদ্ধান্ত সহায় — চৰকাৰী সতৰ্কবাণী নহয়।",
    emergency: "আপৎকালীন: ১১২ লৈ ফোন কৰক",
  },
  bn: {
    title: "আমার এলাকা কি নিরাপদ?",
    subtitle: "পাইলট জেলায় কোনো স্থানের ভূমিধস পরিস্থিতি দেখুন।",
    useLocation: "আমার অবস্থান ব্যবহার করুন",
    chooseDistrict: "অথবা জেলা কেন্দ্র বেছে নিন",
    check: "এই এলাকা পরীক্ষা করুন",
    checking: "পরীক্ষা চলছে…",
    riskHere: "বর্তমান ভূমিধস ঝুঁকি",
    officialAdvisory: "সরকারি সতর্কতা",
    noAdvisory: "এই এলাকার জন্য কোনো সরকারি সতর্কতা সক্রিয় নেই।",
    updated: "শেষ হালনাগাদ",
    safety: "কী করবেন",
    reportHazard: "বিপদ রিপোর্ট করুন",
    hazardType: "আপনি কী দেখেছেন?",
    describe: "সংক্ষেপে বর্ণনা করুন",
    addPhoto: "ছবি যোগ করুন (ঐচ্ছিক)",
    consent: "এই অবস্থান ও ছবি জেলা প্রশাসনের সাথে শেয়ার করতে আমি সম্মতি দিচ্ছি।",
    submit: "রিপোর্ট পাঠান",
    submitting: "পাঠানো হচ্ছে…",
    submitted: "রিপোর্ট পাওয়া গেছে। কর্মকর্তার যাচাই বাকি।",
    pending: "যাচাই বাকি",
    disclaimer: "শুধুমাত্র সিদ্ধান্ত সহায়তা — সরকারি সতর্কতা নয়।",
    emergency: "আপাতকালীন: ১১২ নম্বরে কল করুন",
  },
  ne: {
    title: "मेरो क्षेत्र सुरक्षित छ?",
    subtitle: "पाइलट जिल्लामा कुनै स्थानको पहिरो अवस्था जाँच्नुहोस्।",
    useLocation: "मेरो स्थान प्रयोग गर्नुहोस्",
    chooseDistrict: "वा जिल्ला केन्द्र छान्नुहोस्",
    check: "यो क्षेत्र जाँच्नुहोस्",
    checking: "जाँच भइरहेको छ…",
    riskHere: "हालको पहिरो जोखिम",
    officialAdvisory: "आधिकारिक सूचना",
    noAdvisory: "यो क्षेत्रका लागि कुनै आधिकारिक सूचना सक्रिय छैन।",
    updated: "अन्तिम अद्यावधिक",
    safety: "के गर्ने",
    reportHazard: "जोखिम रिपोर्ट गर्नुहोस्",
    hazardType: "तपाईंले के देख्नुभयो?",
    describe: "छोटकरीमा वर्णन गर्नुहोस्",
    addPhoto: "फोटो थप्नुहोस् (वैकल्पिक)",
    consent: "यो स्थान र फोटो जिल्ला प्रशासनसँग साझा गर्न म सहमति दिन्छु।",
    submit: "रिपोर्ट पठाउनुहोस्",
    submitting: "पठाइँदैछ…",
    submitted: "रिपोर्ट प्राप्त भयो। अधिकारीद्वारा प्रमाणीकरण बाँकी छ।",
    pending: "प्रमाणीकरण बाँकी",
    disclaimer: "निर्णय सहायता मात्र — आधिकारिक चेतावनी होइन।",
    emergency: "आपत्काल: ११२ मा फोन गर्नुहोस्",
  },
};

export function t(lang: Lang): Dict {
  return strings[lang] ?? strings.en;
}
