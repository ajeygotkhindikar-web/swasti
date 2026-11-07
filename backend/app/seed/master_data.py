"""Master data for the 14 SWASTI wellness dimensions.

Every question uses the common 1–5 scale. Reverse-scored items (where a
higher frequency is less healthy, e.g. stress) are flagged in scoring_rule.
References: URLs point at the issuing organisation's public page. They are
seeded with verification_status='pending_verification' and no
last_verified_date. An administrator or domain expert must check each one
and mark it verified in Administration → Evidence.
"""

FREQ = [
    {"value": 1, "label": "Rarely / Never"},
    {"value": 2, "label": "Occasionally"},
    {"value": 3, "label": "Sometimes"},
    {"value": 4, "label": "Frequently"},
    {"value": 5, "label": "Consistently"},
]
LIKERT = [
    {"value": 1, "label": "Very poor"},
    {"value": 2, "label": "Below expectations"},
    {"value": 3, "label": "Moderate"},
    {"value": 4, "label": "Good"},
    {"value": 5, "label": "Very good"},
]
YES_NO = [{"value": 1, "label": "No"}, {"value": 5, "label": "Yes"}]
ACTIVE_DAYS = [
    {"value": 1, "label": "0 days"},
    {"value": 2, "label": "1–2 days"},
    {"value": 3, "label": "3–4 days"},
    {"value": 4, "label": "5–6 days"},
    {"value": 5, "label": "Every day"},
]
EMERGENCY_FUND = [
    {"value": 1, "label": "No emergency savings yet"},
    {"value": 2, "label": "Less than 1 month of expenses"},
    {"value": 3, "label": "1–3 months of expenses"},
    {"value": 4, "label": "3–6 months of expenses"},
    {"value": 5, "label": "More than 6 months of expenses"},
]

OPTIONS = {"likert": LIKERT, "frequency": FREQ, "yes_no": YES_NO}

# (code, name, icon, description, agent_code)
CATEGORIES = [
    ("MEN", "Mental Wellness", "brain", "Work-related stress, concentration, mental fatigue, recovery and work-life balance.", "mental_agent"),
    ("PHY", "Physical Wellness", "heart-pulse", "Sleep, physical activity, energy, sedentary time and preventive health habits.", "physical_agent"),
    ("FIN", "Financial Wellness", "wallet", "Managing expenses, loan burden, emergency preparedness and financial confidence.", "financial_agent"),
    ("PSY", "Psychological Wellness", "shield-check", "Emotional stability, confidence, handling uncertainty and setbacks, sense of purpose.", "psychological_agent"),
    ("SOC", "Social Wellness", "users", "Friendships, community engagement, belonging and freedom from isolation.", "social_agent"),
    ("SPI", "Spiritual Wellness", "sparkles", "Inner peace, reflection, gratitude and values-aligned living — in any tradition or none.", "spiritual_agent"),
    ("FAM", "Family Wellness", "home", "Quality family time, relationships, caregiving and balancing work with family.", "family_agent"),
    ("MUS", "Musical Wellness", "music", "Enjoying, learning and participating in music, including Indian classical and folk traditions.", "musical_agent"),
    ("ENV", "Environmental Wellness", "leaf", "Sustainable habits, waste segregation, time in nature and environmental awareness.", "environmental_agent"),
    ("CIV", "Civic Wellness", "landmark", "Responsible citizenship, community initiatives, volunteering and respect for public spaces.", "civic_agent"),
    ("EMP", "Empathetic Wellness", "hand-heart", "Empathy and kindness towards people, animals and nature.", "empathetic_agent"),
    ("SPO", "Sporting Wellness", "bike", "Recreational sport, endurance activities and making time for play — without comparison.", "sporting_agent"),
    ("CUL", "Cultural Wellness", "palette", "Heritage, regional traditions, literature, arts and values such as tolerance and honesty.", "cultural_agent"),
    ("UNI", "Universal Brotherhood", "globe", "Inclusiveness, respect across communities, dialogue and peaceful coexistence.", "brotherhood_agent"),
]

# category -> list of (name, question, response_type, reverse, options_override)
QUESTIONS = {
    "MEN": [
        ("Work-related stress", "How often do you feel stressed because of work?", "frequency", True, None),
        ("Disconnecting after work", "How often are you able to switch off from work after working hours?", "frequency", False, None),
        ("Mental freshness", "How often do you feel mentally refreshed and able to concentrate?", "frequency", False, None),
        ("Work-life balance", "How satisfied are you with your current work-life balance?", "likert", False, None),
    ],
    "PHY": [
        ("Sleep quality", "How would you rate the quality of your sleep?", "likert", False, None),
        ("Active days", "In a typical week, on how many days are you physically active for about 30 minutes or more?", "range", False, ACTIVE_DAYS),
        ("Sitting breaks", "How often do you take breaks from prolonged sitting?", "frequency", False, None),
        ("Preventive check-ups", "How regularly do you attend preventive health check-ups?", "frequency", False, None),
    ],
    "FIN": [
        ("Monthly expenses", "How comfortable are you managing your monthly expenses?", "likert", False, None),
        ("Loan and EMI burden", "How manageable are your existing loans and EMIs? (Choose Not Applicable if you have none.)", "likert", False, None),
        ("Emergency savings", "Roughly how much emergency savings do you have set aside?", "range", False, EMERGENCY_FUND),
        ("Future commitments", "How confident are you about meeting future commitments such as children's education or family needs?", "likert", False, None),
    ],
    "PSY": [
        ("Handling uncertainty", "How confident do you feel handling unexpected challenges?", "likert", False, None),
        ("Career and job-security worry", "How often do concerns about job security or your career worry you?", "frequency", True, None),
        ("Bouncing back", "How well do you bounce back after setbacks?", "likert", False, None),
        ("Purpose and achievement", "How strong is your sense of purpose and personal achievement?", "likert", False, None),
    ],
    "SOC": [
        ("Meaningful contact", "How often do you meet or talk meaningfully with friends or relatives?", "frequency", False, None),
        ("Loneliness", "How often do you feel lonely or left out?", "frequency", True, None),
        ("Community activities", "How often do you take part in community or group activities outside work?", "frequency", False, None),
        ("Belonging", "How strong is your sense of belonging to a community or circle of people?", "likert", False, None),
    ],
    "SPI": [
        ("Inner peace", "How often do you experience a sense of inner peace?", "frequency", False, None),
        ("Reflection practice", "How often do you set aside time for reflection, meditation, prayer or quiet contemplation — in whatever form is meaningful to you?", "frequency", False, None),
        ("Gratitude", "How often do you consciously feel or express gratitude?", "frequency", False, None),
        ("Values alignment", "How well do your daily decisions align with your personal values and ethics?", "likert", False, None),
    ],
    "FAM": [
        ("Quality family time", "How often do you spend quality, undistracted time with your family?", "frequency", False, None),
        ("Relationship satisfaction", "How satisfied are you with your family relationships and communication?", "likert", False, None),
        ("Balancing work and family", "How well are you able to balance work with family and caregiving responsibilities?", "likert", False, None),
        ("Involvement with children/dependents", "How involved are you in your children's education or your dependents' well-being? (Not Applicable if none.)", "likert", False, None),
    ],
    "MUS": [
        ("Listening to music", "How often do you listen to music you enjoy, without work interruptions?", "frequency", False, None),
        ("Making music", "How often do you sing, play an instrument or take part in music activities?", "frequency", False, None),
        ("Interest in learning", "How interested are you in learning (or continuing to learn) an instrument or vocal music?", "likert", False, None),
        ("Exploring traditions", "How often do you explore Indian classical, folk or other musical traditions?", "frequency", False, None),
    ],
    "ENV": [
        ("Waste segregation", "How regularly do you segregate household waste (wet / dry / hazardous)?", "frequency", False, None),
        ("Responsible consumption", "How often do you make conscious choices to reduce consumption — reusable bags, saving water or electricity?", "frequency", False, None),
        ("Time in nature", "How often do you spend time in nature — parks, gardens, trekking, tree plantation?", "frequency", False, None),
        ("Environmental awareness", "How aware are you of local environmental issues such as air quality, water and biodiversity?", "likert", False, None),
    ],
    "CIV": [
        ("Community initiatives", "How often do you take part in community or local improvement initiatives?", "frequency", False, None),
        ("Volunteering", "How often do you volunteer time for community service?", "frequency", False, None),
        ("Civic awareness", "How well informed are you about your civic responsibilities — voting, local governance, public rules?", "likert", False, None),
        ("Respect for public spaces", "How consistently do you help keep public spaces clean and respected?", "frequency", False, None),
    ],
    "EMP": [
        ("Understanding others", "How often do you make an effort to understand how colleagues or family members feel?", "frequency", False, None),
        ("Compassion towards animals", "How often do you show care towards animals — feeding, helping, avoiding cruelty?", "frequency", False, None),
        ("Supporting the disadvantaged", "How often do you help or support people facing hardship or disadvantage?", "frequency", False, None),
        ("Everyday kindness", "How often do you practise kindness in everyday interactions?", "frequency", False, None),
    ],
    "SPO": [
        ("Playing sport", "How often do you play a sport or recreational game?", "frequency", False, None),
        ("Endurance activities", "How often do you walk, run, cycle, swim, trek or do similar activities for enjoyment?", "frequency", False, None),
        ("Access to facilities", "How easy is it for you to access outdoor spaces or sports facilities?", "likert", False, None),
        ("Making time to play", "How well are you able to make time for sport or play in your week?", "likert", False, None),
    ],
    "CUL": [
        ("Cultural participation", "How often do you take part in cultural events, festivals or performances?", "frequency", False, None),
        ("Literature, art and heritage", "How often do you engage with literature, art or heritage — reading, museums, heritage sites?", "frequency", False, None),
        ("Regional appreciation", "How much do you appreciate traditions and languages of regions other than your own?", "likert", False, None),
        ("Living shared values", "How consistently do you practise values such as tolerance, honesty and mutual respect?", "frequency", False, None),
    ],
    "UNI": [
        ("Inclusiveness", "How comfortable are you working and socialising with people of different communities and backgrounds?", "likert", False, None),
        ("Dialogue in disagreement", "When disagreements arise, how often do you resolve them through calm, respectful dialogue?", "frequency", False, None),
        ("Cooperation beyond your circle", "How often do you cooperate with or support people beyond your immediate circle?", "frequency", False, None),
        ("Peaceful coexistence", "How strongly do you feel committed to peaceful coexistence and equal respect for all?", "likert", False, None),
    ],
}

# Parameters for which "Not Applicable" is a meaningful choice.
NA_ALLOWED = {"FIN_02", "FAM_04"}

# (id, category, title, organisation, url, publication, evidence_level, supporting_evidence)
REFERENCES = [
    ("REF_MEN_1", "MEN", "WHO guidelines on mental health at work", "World Health Organization", "https://www.who.int/publications/i/item/9789240053052", "2022", "International guideline",
     "Recommends organisational interventions, manager training and individual stress-management interventions to protect and promote mental health at work."),
    ("REF_MEN_2", "MEN", "Mental health at work: policy brief", "World Health Organization & International Labour Organization", "https://www.who.int/publications/i/item/9789240057944", "2022", "International policy guidance",
     "Joint WHO/ILO brief on preventing work-related mental health risks, including excessive workloads and long working hours."),
    ("REF_PHY_1", "PHY", "WHO guidelines on physical activity and sedentary behaviour", "World Health Organization", "https://www.who.int/publications/i/item/9789240015128", "2020", "International guideline",
     "Adults should do 150–300 minutes of moderate-intensity activity per week (or equivalent), limit sedentary time and replace it with activity of any intensity; some activity is better than none."),
    ("REF_PHY_2", "PHY", "Fit India Movement", "Government of India (Ministry of Youth Affairs & Sports)", "https://fitindia.gov.in/", None, "National programme",
     "National initiative encouraging everyday physical activity and fitness for all age groups."),
    ("REF_PHY_3", "PHY", "National Health Mission", "Ministry of Health and Family Welfare, Government of India", "https://nhm.gov.in/", None, "National programme",
     "Includes population screening for non-communicable diseases and promotes preventive health check-ups through public health facilities."),
    ("REF_FIN_1", "FIN", "Financial Education resources", "Reserve Bank of India", "https://rbi.org.in/financialeducation/home.aspx", None, "Regulator guidance",
     "Consumer guidance on budgeting, saving, responsible borrowing and safe digital banking."),
    ("REF_FIN_2", "FIN", "Investor education portal", "Securities and Exchange Board of India", "https://investor.sebi.gov.in/", None, "Regulator guidance",
     "Investor education on financial planning, risk and avoiding fraud. SWASTI does not recommend any investment product."),
    ("REF_FIN_3", "FIN", "National Centre for Financial Education", "NCFE (promoted by RBI, SEBI, IRDAI, PFRDA)", "https://ncfe.org.in/", None, "National programme",
     "Free financial literacy material including household budgeting and emergency fund planning."),
    ("REF_PSY_1", "PSY", "Doing What Matters in Times of Stress: an illustrated guide", "World Health Organization", "https://www.who.int/publications/i/item/9789240003927", "2020", "International self-help guide",
     "Evidence-informed self-help skills for managing stress: grounding, unhooking from difficult thoughts, acting on values, being kind."),
    ("REF_PSY_2", "PSY", "Tele-MANAS national tele-mental health programme", "Ministry of Health and Family Welfare, Government of India", "https://telemanas.mohfw.gov.in/", "2022", "National service",
     "Free 24x7 mental health support helpline: 14416 or 1-800-891-4416."),
    ("REF_SOC_1", "SOC", "Social isolation and loneliness", "World Health Organization", "https://www.who.int/teams/social-determinants-of-health/demographic-change-and-healthy-ageing/social-isolation-and-loneliness", None, "International guidance",
     "WHO recognises social isolation and loneliness as public health priorities with effects on physical and mental health."),
    ("REF_SOC_2", "SOC", "Social relationships and mortality risk: a meta-analytic review (Holt-Lunstad, Smith & Layton)", "PLOS Medicine", "https://doi.org/10.1371/journal.pmed.1000316", "2010", "Peer-reviewed meta-analysis",
     "Meta-analysis of 148 studies finding stronger social relationships associated with increased likelihood of survival."),
    ("REF_SPI_1", "SPI", "Counting blessings versus burdens (Emmons & McCullough)", "Journal of Personality and Social Psychology", "https://doi.org/10.1037/0022-3514.84.2.377", "2003", "Peer-reviewed experimental study",
     "Experimental studies in which regular gratitude journaling was associated with improved well-being."),
    ("REF_SPI_2", "SPI", "Doing What Matters in Times of Stress", "World Health Organization", "https://www.who.int/publications/i/item/9789240003927", "2020", "International self-help guide",
     "Includes short, non-religious reflection and grounding practices that people of any belief can use."),
    ("REF_FAM_1", "FAM", "Parenting resources", "UNICEF", "https://www.unicef.org/parenting", None, "International guidance",
     "Practical guidance on positive parenting, communication and spending quality time with children."),
    ("REF_FAM_2", "FAM", "Mental health at work: policy brief (working time and family)", "World Health Organization & International Labour Organization", "https://www.who.int/publications/i/item/9789240057944", "2022", "International policy guidance",
     "Notes long working hours and poor work-life balance as psychosocial risks, including effects on family life."),
    ("REF_MUS_1", "MUS", "What is the evidence on the role of the arts in improving health and well-being? (Fancourt & Finn)", "WHO Regional Office for Europe", "https://www.who.int/europe/publications/i/item/9789289054553", "2019", "Scoping review (900+ publications)",
     "Synthesis of evidence that arts engagement, including music, can support mental and physical health and well-being."),
    ("REF_MUS_2", "MUS", "Sangeet Natak Akademi", "Ministry of Culture, Government of India", "https://www.sangeetnatak.gov.in/", None, "National institution",
     "India's national academy for music, dance and drama; resources on classical and folk traditions."),
    ("REF_ENV_1", "ENV", "Mission LiFE (Lifestyle for Environment)", "Ministry of Environment, Forest and Climate Change, Government of India", "https://missionlife-moefcc.nic.in/", "2022", "National programme",
     "Promotes individual actions such as saving energy and water, reducing single-use plastic and waste, and sustainable food systems."),
    ("REF_ENV_2", "ENV", "Ministry of Environment, Forest and Climate Change", "Government of India", "https://moef.gov.in/", None, "Government guidance",
     "Publishes the Solid Waste Management Rules, 2016 requiring source segregation of waste."),
    ("REF_ENV_3", "ENV", "UN Environment Programme", "UNEP", "https://www.unep.org/", None, "International guidance",
     "Guidance on sustainable consumption, biodiversity and pollution reduction."),
    ("REF_CIV_1", "CIV", "MY Bharat volunteering platform", "Ministry of Youth Affairs & Sports, Government of India", "https://mybharat.gov.in/", "2023", "National programme",
     "Platform listing volunteering and community-service opportunities."),
    ("REF_CIV_2", "CIV", "Constitution of India — Fundamental Duties (Article 51A)", "Legislative Department, Government of India", "https://www.legislative.gov.in/constitution-of-india/", "1976", "Constitutional text",
     "Lists citizens' duties including protecting public property, the environment, and promoting harmony and brotherhood."),
    ("REF_CIV_3", "CIV", "United Nations Volunteers", "UNV", "https://www.unv.org/", None, "International guidance",
     "Evidence and resources on the social value of volunteerism."),
    ("REF_EMP_1", "EMP", "Happy to help? A systematic review and meta-analysis of the effects of performing acts of kindness (Curry et al.)", "Journal of Experimental Social Psychology", "https://doi.org/10.1016/j.jesp.2018.02.014", "2018", "Peer-reviewed meta-analysis",
     "Performing acts of kindness had a small-to-medium positive effect on the well-being of the actor."),
    ("REF_EMP_2", "EMP", "Animal Welfare Board of India", "Government of India", "https://awbi.gov.in/", None, "Statutory body",
     "Guidance on humane treatment of animals under the Prevention of Cruelty to Animals Act, 1960."),
    ("REF_SPO_1", "SPO", "WHO guidelines on physical activity and sedentary behaviour", "World Health Organization", "https://www.who.int/publications/i/item/9789240015128", "2020", "International guideline",
     "Recreational sport and active leisure count toward recommended activity; any activity is better than none."),
    ("REF_SPO_2", "SPO", "Khelo India", "Ministry of Youth Affairs & Sports, Government of India", "https://kheloindia.gov.in/", None, "National programme",
     "National programme for mass participation in sport."),
    ("REF_CUL_1", "CUL", "Intangible Cultural Heritage — India", "UNESCO", "https://ich.unesco.org/en/state/india-IN", None, "International register",
     "UNESCO-inscribed elements of India's living heritage such as Yoga, Kumbh Mela, Durga Puja in Kolkata, Garba of Gujarat and Vedic chanting."),
    ("REF_CUL_2", "CUL", "Ministry of Culture", "Government of India", "https://www.indiaculture.gov.in/", None, "Government guidance",
     "Information on museums, heritage sites, libraries and cultural programmes."),
    ("REF_UNI_1", "UNI", "International Day for Tolerance / Declaration of Principles on Tolerance", "UNESCO", "https://www.unesco.org/en/days/tolerance", "1995", "International declaration",
     "Defines tolerance as respect, acceptance and appreciation of the rich diversity of cultures and ways of being human."),
    ("REF_UNI_2", "UNI", "Declaration and Programme of Action on a Culture of Peace (A/RES/53/243)", "United Nations General Assembly", "https://www.un.org/en/ga/search/view_doc.asp?symbol=A/RES/53/243", "1999", "International declaration",
     "Promotes dialogue, cooperation and non-violent conflict resolution."),
]

# (id, category, title, description, action, micro_habit, frequency, ref, target_params, priority)
RECOMMENDATIONS = [
    ("REC_MEN_1", "MEN", "Short recovery breaks", "Brief breaks during the working day help recovery from sustained mental effort.", "Schedule a 5-minute screen-free break every 90 minutes of focused work.", "Take a short mindful break", "daily", "REF_MEN_1", ["MEN_01", "MEN_03"], 1),
    ("REC_MEN_2", "MEN", "Clear work–personal boundaries", "Defined end-of-work routines reduce after-hours work spill-over.", "Choose an end-of-work time on most days and close work apps after it.", "Close work apps at your chosen end time", "daily", "REF_MEN_2", ["MEN_02", "MEN_04"], 1),
    ("REC_MEN_3", "MEN", "Practise a relaxation technique", "Evidence-based stress-management skills such as grounding can be learned and practised.", "Try one grounding exercise from WHO's 'Doing What Matters' guide.", "Two minutes of slow breathing or grounding", "daily", "REF_PSY_1", ["MEN_01", "MEN_03"], 2),
    ("REC_MEN_4", "MEN", "Seek qualified support when needed", "If stress persists or feels unmanageable, talking to a qualified professional helps.", "Speak with a qualified counsellor, or call Tele-MANAS (14416) for free support.", "Check in with yourself: how am I really doing?", "weekly", "REF_PSY_2", ["MEN_01"], 2),
    ("REC_PHY_1", "PHY", "Build regular physical activity", "WHO recommends regular moderate activity for adults; some is better than none.", "Add a brisk walk or other activity you enjoy on a few days this week; build gradually.", "A 10-minute brisk walk", "daily", "REF_PHY_1", ["PHY_02"], 1),
    ("REC_PHY_2", "PHY", "Interrupt prolonged sitting", "Replacing sedentary time with light activity has health benefits.", "Stand up and move for 2–3 minutes every hour of sitting.", "Movement break each hour", "daily", "REF_PHY_1", ["PHY_03"], 1),
    ("REC_PHY_3", "PHY", "Consistent sleep routine", "Regular sleep and wake times and a screen-free wind-down support sleep quality.", "Keep a consistent bedtime and put screens away 30 minutes before sleep.", "Screen-free wind-down before bed", "daily", "REF_PHY_1", ["PHY_01"], 2),
    ("REC_PHY_4", "PHY", "Preventive health check-ups", "Periodic screening helps detect conditions early; ask your doctor what suits your age.", "Book a preventive check-up or NCD screening at a nearby facility.", "Note one health question for your next doctor visit", "weekly", "REF_PHY_3", ["PHY_04"], 2),
    ("REC_FIN_1", "FIN", "Household budget", "A simple budget makes monthly expenses visible and manageable.", "List fixed and variable expenses for one month using an RBI/NCFE budgeting template.", "Review today's discretionary expenses", "daily", "REF_FIN_3", ["FIN_01"], 1),
    ("REC_FIN_2", "FIN", "Review loan obligations", "Knowing interest rates and EMIs helps you prioritise repayments.", "List each loan with its interest rate and EMI; consider prepaying the costliest first.", "Check one loan statement this week", "weekly", "REF_FIN_1", ["FIN_02"], 1),
    ("REC_FIN_3", "FIN", "Start an emergency fund", "An emergency buffer sized to your circumstances reduces financial stress.", "Set aside a small fixed amount each month into a separate savings account.", "Move a small amount to savings", "weekly", "REF_FIN_3", ["FIN_03"], 1),
    ("REC_FIN_4", "FIN", "Improve financial literacy", "Understanding risk and fraud protects long-term goals. SWASTI does not recommend investment products.", "Read one module on SEBI's investor education portal.", "Learn one financial concept", "weekly", "REF_FIN_2", ["FIN_04"], 3),
    ("REC_PSY_1", "PSY", "Reflect on achievements", "Recognising progress supports confidence and resilience.", "Each week, note three things you handled well.", "Write down one thing you did well", "daily", "REF_PSY_1", ["PSY_01", "PSY_04"], 2),
    ("REC_PSY_2", "PSY", "Unhook from worrying thoughts", "Noticing and naming difficult thoughts reduces their pull.", "When career worries arise, name the thought and return attention to the present task.", "Name one worry and let it pass", "daily", "REF_PSY_1", ["PSY_02"], 1),
    ("REC_PSY_3", "PSY", "Talk to someone you trust", "Support from others helps people recover from setbacks. Professional help is available.", "Share a recent setback with a trusted person, or contact Tele-MANAS (14416).", "Reach out to one supportive person", "weekly", "REF_PSY_2", ["PSY_03"], 2),
    ("REC_SOC_1", "SOC", "Regular meaningful contact", "Strong social relationships are associated with better health outcomes.", "Call or meet one friend or relative each week.", "Connect with a friend or relative", "weekly", "REF_SOC_2", ["SOC_01", "SOC_02"], 1),
    ("REC_SOC_2", "SOC", "Join a group activity", "Group activities build belonging and reduce isolation.", "Join a local club, walking group, class or residents' association activity.", "Attend one group activity", "weekly", "REF_SOC_1", ["SOC_03", "SOC_04"], 2),
    ("REC_SPI_1", "SPI", "Daily reflection", "A few minutes of quiet reflection, in any tradition or none, supports inner calm.", "Spend a few minutes in quiet reflection, meditation or prayer — whatever is meaningful to you.", "Five minutes of quiet reflection", "daily", "REF_SPI_2", ["SPI_01", "SPI_02"], 1),
    ("REC_SPI_2", "SPI", "Gratitude practice", "Regularly noting things you are grateful for is associated with improved well-being.", "Write down three things you are grateful for, a few times a week.", "Note three things you're grateful for", "daily", "REF_SPI_1", ["SPI_03"], 2),
    ("REC_SPI_3", "SPI", "Act on your values", "Choosing small actions aligned with your values builds a sense of purpose.", "Pick one personal value and one small action that reflects it this week.", "One values-aligned action", "weekly", "REF_SPI_2", ["SPI_04"], 3),
    ("REC_FAM_1", "FAM", "Dedicated family time", "Regular undistracted time strengthens family relationships.", "Set a phone-free family meal or conversation time on most days.", "Phone-free family conversation", "daily", "REF_FAM_1", ["FAM_01", "FAM_02"], 1),
    ("REC_FAM_2", "FAM", "Active listening", "Listening without interrupting improves family communication.", "In one conversation each day, listen fully before responding.", "Listen fully in one conversation", "daily", "REF_FAM_1", ["FAM_02"], 2),
    ("REC_FAM_3", "FAM", "Engage in children's learning", "Parental involvement supports children's development.", "Spend time on one of your child's school or hobby activities each week.", "Ask your child about their day", "daily", "REF_FAM_1", ["FAM_04"], 2),
    ("REC_FAM_4", "FAM", "Plan a shared family activity", "Shared activities create positive family time and can be planned around work demands.", "Plan one shared outing or activity this month and protect that time.", "Plan a family activity", "weekly", "REF_FAM_2", ["FAM_03"], 2),
    ("REC_MUS_1", "MUS", "Protected music time", "Engaging with music is associated with mood and well-being benefits.", "Schedule 15 minutes to listen to music you love, without multitasking.", "Listen to a favourite composition", "daily", "REF_MUS_1", ["MUS_01"], 1),
    ("REC_MUS_2", "MUS", "Learn or revisit an instrument", "Active music-making offers additional cognitive and social benefits.", "Try a beginner lesson in an instrument or vocal music.", "Ten minutes of practice", "weekly", "REF_MUS_1", ["MUS_02", "MUS_03"], 2),
    ("REC_MUS_3", "MUS", "Explore Indian music traditions", "India's classical and folk traditions offer rich listening.", "Listen to one raga or folk form you haven't heard before.", "Discover one new raga or folk song", "weekly", "REF_MUS_2", ["MUS_04"], 3),
    ("REC_ENV_1", "ENV", "Segregate waste at source", "Source segregation is required under India's Solid Waste Management Rules, 2016.", "Keep separate bins for wet, dry and hazardous waste at home.", "Segregate today's waste", "daily", "REF_ENV_2", ["ENV_01"], 1),
    ("REC_ENV_2", "ENV", "Responsible consumption", "Mission LiFE promotes small individual actions that reduce environmental impact.", "Pick one LiFE action this week: carry a cloth bag, switch off idle appliances, or save water.", "One Mission LiFE action", "daily", "REF_ENV_1", ["ENV_02"], 1),
    ("REC_ENV_3", "ENV", "Nature time and local initiatives", "Time in nature and participation in local drives build environmental connection.", "Visit a park or join a local tree-plantation or clean-up drive.", "Spend time outdoors in nature", "weekly", "REF_ENV_3", ["ENV_03", "ENV_04"], 2),
    ("REC_CIV_1", "CIV", "Small community contribution", "Volunteering benefits communities and volunteers.", "Find one local volunteering opportunity on MY Bharat or in your neighbourhood.", "Do one small community activity", "weekly", "REF_CIV_1", ["CIV_01", "CIV_02"], 1),
    ("REC_CIV_2", "CIV", "Know your civic duties", "Article 51A lists duties including protecting public property and promoting harmony.", "Read the Fundamental Duties and check your voter registration.", "Learn one civic fact", "weekly", "REF_CIV_2", ["CIV_03", "CIV_04"], 2),
    ("REC_EMP_1", "EMP", "Intentional acts of kindness", "Performing acts of kindness is associated with improved well-being.", "Plan one deliberate act of kindness each day.", "Perform an intentional act of kindness", "daily", "REF_EMP_1", ["EMP_04", "EMP_03"], 1),
    ("REC_EMP_2", "EMP", "Perspective-taking", "Pausing to understand another's view strengthens relationships at work and home.", "Before responding in a tense moment, ask how the other person may be feeling.", "Ask someone how they are really doing", "daily", "REF_EMP_1", ["EMP_01"], 2),
    ("REC_EMP_3", "EMP", "Compassion for animals", "Humane treatment of animals is a shared responsibility.", "Provide water for birds or animals in summer, or support a local animal shelter.", "One caring act for animals", "weekly", "REF_EMP_2", ["EMP_02"], 3),
    ("REC_SPO_1", "SPO", "Recreational sport", "Recreational sport counts toward physical activity and adds social enjoyment.", "Play a sport or game you enjoy with friends or family — no targets, just play.", "Participate in a recreational activity", "weekly", "REF_SPO_1", ["SPO_01", "SPO_04"], 1),
    ("REC_SPO_2", "SPO", "Enjoyable endurance activity", "Walking, cycling or swimming at your own pace supports fitness.", "Try a weekend walk, cycle or trek at a comfortable pace.", "A short walk or cycle for enjoyment", "weekly", "REF_SPO_1", ["SPO_02"], 2),
    ("REC_SPO_3", "SPO", "Find accessible facilities", "National programmes widen access to sports facilities and events.", "Look for a public ground, park or community sports event near you.", "Find one nearby place to play", "weekly", "REF_SPO_2", ["SPO_03"], 3),
    ("REC_CUL_1", "CUL", "Explore heritage", "Engaging with heritage builds cultural awareness and connection.", "Visit a museum, heritage site or library, or read about a UNESCO-listed Indian tradition.", "Explore a cultural or literary work", "weekly", "REF_CUL_1", ["CUL_02", "CUL_01"], 1),
    ("REC_CUL_2", "CUL", "Appreciate other regions", "Learning about other regions' traditions builds respect for diversity.", "Learn a greeting or folk tradition from another Indian state.", "Learn one thing about another region", "weekly", "REF_CUL_2", ["CUL_03", "CUL_04"], 2),
    ("REC_UNI_1", "UNI", "Respectful dialogue", "Dialogue and non-violent conflict resolution are central to a culture of peace.", "In your next disagreement, summarise the other view before giving yours.", "Practise respectful dialogue", "daily", "REF_UNI_2", ["UNI_02"], 1),
    ("REC_UNI_2", "UNI", "Connect across communities", "Contact across communities builds tolerance and mutual respect.", "Join an inter-community event, or share a meal with someone from a different background.", "Have a conversation with someone from a different background", "weekly", "REF_UNI_1", ["UNI_01", "UNI_04"], 2),
    ("REC_UNI_3", "UNI", "Cooperate beyond your circle", "Mutual support across groups strengthens communities.", "Offer help to a neighbour or colleague outside your usual circle.", "Offer help to someone new", "weekly", "REF_UNI_2", ["UNI_03"], 2),
]

AGENT_DESCRIPTIONS = {
    "MEN": "Analyses stress, recovery and work-life balance. Flags crisis language for human escalation; never diagnoses.",
    "PHY": "Analyses sleep, activity, sedentary time and preventive habits against WHO guidance; never prescribes treatment.",
    "FIN": "Analyses budgeting comfort, debt burden and emergency preparedness; never recommends investment products.",
    "PSY": "Analyses confidence, resilience and career worry; recommends qualified support where appropriate, never diagnoses.",
    "SOC": "Analyses social contact, loneliness and belonging.",
    "SPI": "Analyses reflection, gratitude and inner peace without favouring any religion or belief system.",
    "FAM": "Analyses family time, communication and work-family balance.",
    "MUS": "Analyses music listening, participation and exploration of musical traditions.",
    "ENV": "Analyses sustainable habits and connection with nature.",
    "CIV": "Analyses civic participation, volunteering and respect for public spaces.",
    "EMP": "Analyses empathy and kindness towards people, animals and nature.",
    "SPO": "Analyses recreational sport and play without performance comparison.",
    "CUL": "Analyses cultural participation, heritage engagement and lived values.",
    "UNI": "Analyses inclusiveness, dialogue and peaceful coexistence.",
}

DEFAULT_LEVELS = [
    {"min": 0, "max": 39.99, "level": "Needs Attention", "color": "red"},
    {"min": 40, "max": 59.99, "level": "Developing", "color": "amber"},
    {"min": 60, "max": 74.99, "level": "Balanced", "color": "blue"},
    {"min": 75, "max": 89.99, "level": "Good", "color": "green"},
    {"min": 90, "max": 100, "level": "Thriving", "color": "purple"},
]

DEFAULT_SCORING = {
    "min_category_coverage": 0.5,  # at least 2 of 4 answers needed for a category score
    "min_categories_for_overall": 10,  # overall indicator only if ≥10 of 14 categories scored
    "attention_threshold": 40,
    "quarterly_step": 10,  # max realistic improvement used to set an achievable target
}
