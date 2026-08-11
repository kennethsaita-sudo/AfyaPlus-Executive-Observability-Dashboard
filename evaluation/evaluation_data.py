# evaluation_data.py

evaluation_dataset = [

    # =========================
    # USSD
    # =========================

    {
        "feature": "USSD",
        "question": "How can I check my blood pressure using AfyaPlus?",
        "clinical_reference": "Users should enter recent blood pressure readings measured with an approved device and consult a clinician if readings are elevated."
    },

    {
        "feature": "USSD",
        "question": "What should I do if my blood sugar is above 200 mg/dL?",
        "clinical_reference": "Patients should follow physician guidance, monitor symptoms, maintain hydration and seek urgent care if severe symptoms occur."
    },

    {
        "feature": "USSD",
        "question": "Can AfyaPlus remind me to take medicine?",
        "clinical_reference": "Yes. AfyaPlus supports medication reminders based on schedules configured by the patient or healthcare provider."
    },

    {
        "feature": "USSD",
        "question": "What symptoms may indicate malaria?",
        "clinical_reference": "Common symptoms include fever, chills, headache, fatigue, and body aches. Laboratory confirmation is recommended."
    },

    {
        "feature": "USSD",
        "question": "When should I visit a clinic for persistent fever?",
        "clinical_reference": "Persistent fever lasting more than several days or accompanied by severe symptoms should be medically evaluated."
    },

    # =========================
    # MOBILE APP
    # =========================

    {
        "feature": "Mobile App",
        "question": "How can I upload lab results?",
        "clinical_reference": "Users can upload laboratory result documents through the medical records section of the mobile application."
    },

    {
        "feature": "Mobile App",
        "question": "Does AfyaPlus support telemedicine consultations?",
        "clinical_reference": "Patients may schedule or join virtual consultations when supported by participating providers."
    },

    {
        "feature": "Mobile App",
        "question": "How should I store insulin during travel?",
        "clinical_reference": "Insulin should generally be kept within recommended temperature ranges and protected from extreme heat or freezing."
    },

    {
        "feature": "Mobile App",
        "question": "Can I receive vaccination reminders?",
        "clinical_reference": "The platform may provide vaccination scheduling and reminder notifications."
    },

    {
        "feature": "Mobile App",
        "question": "What should I do after missing a medication dose?",
        "clinical_reference": "Patients should follow medication instructions or seek professional guidance regarding missed doses."
    },

    # =========================
    # WEB PORTAL
    # =========================

    {
        "feature": "Web Portal",
        "question": "How do clinicians review AI recommendations?",
        "clinical_reference": "Clinicians access recommendation history and supporting evidence through the provider portal."
    },

    {
        "feature": "Web Portal",
        "question": "Can clinicians export patient summaries?",
        "clinical_reference": "Authorized healthcare professionals can generate and export approved clinical summaries."
    },

    {
        "feature": "Web Portal",
        "question": "How is patient privacy protected?",
        "clinical_reference": "Patient data should be protected using encryption, access controls and healthcare privacy practices."
    },

    {
        "feature": "Web Portal",
        "question": "How can audit logs be reviewed?",
        "clinical_reference": "Authorized administrators may inspect audit logs through governance and monitoring interfaces."
    },

    {
        "feature": "Web Portal",
        "question": "What happens when the AI is uncertain?",
        "clinical_reference": "Low-confidence responses should be escalated for human review and verification."
    }

]