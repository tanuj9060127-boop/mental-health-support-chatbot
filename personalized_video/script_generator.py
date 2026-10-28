
"""Generate short, supportive, problem-specific narration scripts.

Only controlled labels and predefined guidance are used in spoken content.
The user's raw message is never read aloud or sent to a speech provider.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = {"en", "hi"}

_PROBLEM_LABELS = {
    "en": {
        "academic_pressure": "academic pressure",
        "parental_expectations": "family expectations",
        "friend_conflict": "a disagreement with someone",
        "loneliness": "feeling disconnected",
        "concentration": "difficulty focusing",
        "sleep_difficulty": "sleep difficulties",
        "work_pressure": "work or deadline pressure",
        "family_related_concern": "a family concern",
        "academic_related_concern": "a study-related concern",
        "work_related_concern": "a work-related concern",
        "general_wellbeing_concern": "a difficult situation",
    },
    "hi": {
        "academic_pressure": "पढ़ाई या परीक्षा का दबाव",
        "parental_expectations": "परिवार की अपेक्षाएँ",
        "friend_conflict": "किसी के साथ मतभेद",
        "loneliness": "अकेलापन या दूसरों से दूरी महसूस करना",
        "concentration": "ध्यान लगाने में कठिनाई",
        "sleep_difficulty": "नींद से जुड़ी कठिनाई",
        "work_pressure": "काम या समय-सीमा का दबाव",
        "family_related_concern": "परिवार से जुड़ी चिंता",
        "academic_related_concern": "पढ़ाई से जुड़ी चिंता",
        "work_related_concern": "काम से जुड़ी चिंता",
        "general_wellbeing_concern": "किसी कठिन परिस्थिति से गुजरना",
    },
}

_CONTEXT_LABELS = {
    "en": {
        "academic": "studies or exams",
        "family": "family",
        "friendship": "friendships",
        "work": "work",
        "relationships": "relationships",
        "social": "social connection",
        "sleep": "sleep",
        "focus": "concentration",
    },
    "hi": {
        "academic": "पढ़ाई या परीक्षाएँ",
        "family": "परिवार",
        "friendship": "दोस्ती",
        "work": "काम",
        "relationships": "रिश्ते",
        "social": "सामाजिक जुड़ाव",
        "sleep": "नींद",
        "focus": "ध्यान लगाना",
    },
}

# Each entry contains controlled, predefined guidance.
# No raw user message is included in the narration.
_GUIDANCE = {
    "en": {
        "work_pressure": [
            "Write down the tasks you need to complete.",
            "Mark their deadlines and identify which task is most urgent.",
            "Choose one realistic task to begin with, and break it into smaller steps.",
            "If two deadlines conflict, ask your supervisor or teammate which task should take priority.",
        ],
        "work_related_concern": [
            "Write down the main work issue and identify what needs attention first.",
            "Break the next task into a few manageable steps.",
            "If expectations are unclear, ask a supervisor or trusted teammate for clarification.",
        ],
        "academic_pressure": [
            "List your subjects, assignments, and upcoming exam dates.",
            "Choose one important topic and study it in a short, focused session.",
            "Take a brief break before deciding what to work on next.",
        ],
        "academic_related_concern": [
            "Write down the study tasks that are worrying you.",
            "Choose one manageable task and divide it into smaller steps.",
            "Use a realistic study schedule that also leaves time for breaks and sleep.",
        ],
        "parental_expectations": [
            "Identify which expectations are creating the most pressure for you.",
            "Think about what you want your family to understand.",
            "Consider explaining your feelings and goals calmly to someone you trust.",
        ],
        "friend_conflict": [
            "Give yourself time to understand what upset you before responding.",
            "Separate what you know happened from what you are assuming.",
            "When you feel ready, explain your perspective calmly and listen to the other person's perspective.",
        ],
        "loneliness": [
            "Think of one person you feel comfortable contacting.",
            "Consider starting with a short message or a brief conversation.",
            "Choose one activity that helps you feel connected to your interests or community.",
        ],
        "concentration": [
            "Choose one small task instead of trying to do everything at once.",
            "Put away unnecessary distractions for a short period.",
            "Work in a manageable session, then take a brief break.",
        ],
        "sleep_difficulty": [
            "Try keeping a consistent bedtime and wake-up time.",
            "Create a calm wind-down routine before bed.",
            "If sleep difficulties persist, consider discussing them with a healthcare professional.",
        ],
        "family_related_concern": [
            "Identify the part of the family situation that you can address right now.",
            "Give yourself time to think before having a difficult conversation.",
            "Consider speaking with a trusted person who can listen without judgment.",
        ],
        "general_wellbeing_concern": [
            "Pause and identify what feels most important right now.",
            "Choose one small action that is within your control.",
            "Consider reaching out to someone you trust for support.",
        ],
    },
    "hi": {
        "work_pressure": [
            "सबसे पहले, पूरे किए जाने वाले कामों की एक सूची बनाएँ।",
            "हर काम की समय-सीमा लिखें और पहचानें कि कौन-सा काम सबसे ज़रूरी है।",
            "एक व्यावहारिक काम चुनें और उसे छोटे-छोटे चरणों में बाँटें।",
            "अगर दो कामों की समय-सीमा टकरा रही है, तो अपने सुपरवाइज़र या टीम के सदस्य से प्राथमिकता स्पष्ट करने को कहें।",
        ],
        "work_related_concern": [
            "काम से जुड़ी मुख्य समस्या लिखें और तय करें कि किस बात पर पहले ध्यान देना है।",
            "अगले काम को कुछ आसान चरणों में बाँटें।",
            "अगर अपेक्षाएँ स्पष्ट नहीं हैं, तो सुपरवाइज़र या भरोसेमंद सहकर्मी से स्पष्टीकरण माँगें।",
        ],
        "academic_pressure": [
            "अपने विषयों, असाइनमेंट और आने वाली परीक्षाओं की सूची बनाएँ।",
            "एक ज़रूरी विषय चुनें और थोड़े समय के लिए उस पर ध्यान दें।",
            "अगला काम चुनने से पहले थोड़ा विराम लें।",
        ],
        "academic_related_concern": [
            "उन पढ़ाई के कामों को लिखें जिनकी वजह से चिंता हो रही है।",
            "एक आसान काम चुनें और उसे छोटे चरणों में बाँटें।",
            "ऐसा पढ़ाई का समय तय करें जिसमें आराम और नींद के लिए भी समय हो।",
        ],
        "parental_expectations": [
            "पहचानें कि परिवार की किन अपेक्षाओं से सबसे ज़्यादा दबाव महसूस हो रहा है।",
            "सोचें कि आप अपने परिवार को कौन-सी बात समझाना चाहते हैं।",
            "अपनी भावनाओं और लक्ष्यों के बारे में किसी भरोसेमंद व्यक्ति से शांत ढंग से बात करने पर विचार करें।",
        ],
        "friend_conflict": [
            "जवाब देने से पहले अपनी भावनाओं को समझने के लिए थोड़ा समय लें।",
            "जो वास्तव में हुआ है और जिसके बारे में आप अनुमान लगा रहे हैं, उनमें अंतर करें।",
            "तैयार महसूस होने पर अपनी बात शांत ढंग से रखें और दूसरे व्यक्ति की बात भी सुनें।",
        ],
        "loneliness": [
            "ऐसे एक व्यक्ति के बारे में सोचें जिससे बात करने में आप सहज महसूस करते हैं।",
            "एक छोटे संदेश या थोड़ी बातचीत से शुरुआत करने पर विचार करें।",
            "ऐसी गतिविधि चुनें जो आपको अपनी रुचियों या समुदाय से जुड़ने में मदद करे।",
        ],
        "concentration": [
            "एक साथ सब कुछ करने के बजाय एक छोटा काम चुनें।",
            "कुछ समय के लिए अनावश्यक ध्यान भटकाने वाली चीज़ों को दूर रखें।",
            "थोड़े समय तक काम करें और फिर एक छोटा विराम लें।",
        ],
        "sleep_difficulty": [
            "सोने और जागने का समय नियमित रखने की कोशिश करें।",
            "सोने से पहले शांत दिनचर्या बनाएँ।",
            "अगर नींद की समस्या लगातार बनी रहती है, तो स्वास्थ्य विशेषज्ञ से बात करने पर विचार करें।",
        ],
        "family_related_concern": [
            "पहचानें कि परिवार से जुड़ी परिस्थिति में अभी किस बात पर ध्यान दिया जा सकता है।",
            "किसी कठिन बातचीत से पहले सोचने के लिए समय लें।",
            "किसी ऐसे भरोसेमंद व्यक्ति से बात करने पर विचार करें जो बिना आलोचना किए आपकी बात सुने।",
        ],
        "general_wellbeing_concern": [
            "थोड़ा रुकें और पहचानें कि इस समय सबसे ज़रूरी बात क्या है।",
            "ऐसा एक छोटा कदम चुनें जो आपके नियंत्रण में है।",
            "सहायता के लिए किसी भरोसेमंद व्यक्ति से बात करने पर विचार करें।",
        ],
    },
}


def _safe_labels(profile: dict, language: str) -> tuple[str, str]:
    problem_map = _PROBLEM_LABELS[language]
    problem_key = str(
        (profile or {}).get("primary_problem")
        or "general_wellbeing_concern"
    )
    problem = problem_map.get(
        problem_key,
        problem_map["general_wellbeing_concern"],
    )

    context_map = _CONTEXT_LABELS[language]
    contexts = (profile or {}).get("contexts") or []

    if not isinstance(contexts, (list, tuple, set)):
        contexts = []

    context_values = [
        context_map[item]
        for item in contexts
        if isinstance(item, str) and item in context_map
    ]

    context = ", ".join(dict.fromkeys(context_values))
    return problem, context


def generate_script(profile: dict, language: str = "en") -> dict:
    """Generate a supportive script tailored to a controlled problem label."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Video language must be 'en' or 'hi'.")

    profile = profile or {}
    problem, context = _safe_labels(profile, language)

    problem_key = str(
        profile.get("primary_problem")
        or "general_wellbeing_concern"
    )

    guidance_map = _GUIDANCE[language]
    guidance = guidance_map.get(
        problem_key,
        guidance_map["general_wellbeing_concern"],
    )

    if language == "hi":
        title = f"{problem} के लिए एक छोटा मार्गदर्शक"
        opening = (
            f"{problem} कभी-कभी मुश्किल लग सकता है। "
            "ऐसी परिस्थिति में परेशान महसूस करना समझ में आता है।"
        )
        context_sentence = (
            f"यह मार्गदर्शक {context} से जुड़ी परिस्थिति पर ध्यान देता है।"
            if context
            else "यह मार्गदर्शक आपकी परिस्थिति में छोटे, व्यावहारिक कदमों पर ध्यान देता है।"
        )
        sections = [
            opening,
            context_sentence,
            "आपको हर समस्या एक ही बार में हल करने की ज़रूरत नहीं है।",
            *guidance,
            "एक छोटा कदम उठाने के बाद रुककर देखें कि आगे किस सहायता की ज़रूरत है।",
            "अगर यह कठिनाई लगातार बनी रहती है या रोज़मर्रा के जीवन पर असर डालती है, तो किसी भरोसेमंद वयस्क या योग्य मानसिक-स्वास्थ्य पेशेवर से बात करने पर विचार करें।",
            "यह वीडियो सामान्य शैक्षिक जानकारी देता है। यह निदान या पेशेवर देखभाल का विकल्प नहीं है।",
        ]
    else:
        title = f"A short guide for {problem.title()}"
        context_sentence = (
            f"This guide focuses on a situation related to {context}."
            if context
            else f"This guide focuses on practical steps for {problem}."
        )
        sections = [
            f"Sometimes {problem} can feel difficult. It is understandable to feel concerned when a situation is challenging.",
            context_sentence,
            "You do not need to solve every problem at once.",
            *guidance,
            "After taking one small step, pause and consider what support or action would help next.",
            "If the difficulty continues or starts to interfere with daily life, consider talking with a trusted adult or a qualified mental-health professional.",
            "This video provides general educational support. It is not a diagnosis or a substitute for professional care.",
        ]

    return {
        "title": title,
        "sections": sections,
        "language": language,
    }
