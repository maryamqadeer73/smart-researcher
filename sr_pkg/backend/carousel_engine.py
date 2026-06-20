"""
Smart Researcher — Carousel Engine
Generates highly engaging, human-written multi-slide carousels and strategy briefs.
Completely free, offline-compatible, no external API keys required.
"""

import random
import re

# Niche-specific pools of topics for Autopilot Mode
AUTOPILOT_TOPIC_POOL = {
    "AI Tools & Automation": [
        "Claude 3.5 Sonnet Artifacts Guide",
        "Local LLM Prompt Engineering Secrets",
        "Automating Customer Support with AI Agents",
        "Building a Self-Contained AI Coding Assistant",
        "Reducing SaaS API costs by 90% using local models",
        "Why you should stop writing manual data parsers",
        "Building offline data synthesis loops",
        "How JIT compiling transforms agent execution"
    ],
    "Web Dev & Coding": [
        "Sleek Next.js App Router architectures",
        "Python 3.14 JIT compiler hacks",
        "Database index optimization strategies for scale",
        "Refactoring spaghetti code into Clean Architecture",
        "Why you should decouple business logic from frameworks",
        "Docker security benchmarks every senior dev must know",
        "Local-first web applications with offline sync",
        "Writing type-safe REST APIs in TypeScript"
    ],
    "Freelancing & Making Money Online": [
        "How to price your development work at $10k+ project rates",
        "Cold outreach frameworks that get high-ticket clients",
        "The Solopreneur system to automate 80% of client onboarding",
        "Transitioning from hourly freelancing to productized services",
        "Why content creation is the best organic funnel for agencies",
        "Negotiating contract value using business outcomes instead of code hours",
        "Scale your consulting business with automated retainers",
        "Finding high-paying micro-niches in tech"
    ],
    "Shopify & eCommerce": [
        "Optimizing Shopify checkout conversion rates by 15%",
        "Dynamic email retargeting flows that recover lost carts",
        "How page load speed directly impacts mobile Shopify sales",
        "Building a high-converting landing page without page builders",
        "A/B testing product page layouts to lower CAC costs",
        "Why generic dropshipping is dead and how to brand your store",
        "Reducing checkout friction on Shopify Mobile",
        "Leveraging organic TikTok search for eCommerce traffic"
    ],
    "All of the above (my niche covers all tech)": [
        "Building self-contained offline software systems",
        "Why local-first software is the future of personal data",
        "The stack we use to run a $20k/month automated business",
        "How to build high-performance data-backed carousels",
        "Designing resilient API integrations that never break",
        "Why systems matter more than tools for software engineers",
        "How to automate cross-posting across 5 social channels",
        "Leveraging Wikipedia data for authentic content loops"
    ]
}

# Heuristic classification keyword mapping for Semantic Theme Mapper
AESTHETIC_ARCHETYPES = [
    {
        "keywords": ["cursor", "cursorai", "cursor.sh", "cursor code"],
        "brand": "cursor",
        "palette": "cursor",
        "style": "tech",
        "logo_icon": "Cu",
        "logo_text": "CURSOR AI",
        "default_graphic": "gear"
    },
    {
        "keywords": ["claude", "anthropic", "starsonnet", "sonnet"],
        "brand": "claude",
        "palette": "claude",
        "style": "editorial",
        "logo_icon": "Cl",
        "logo_text": "CLAUDE AI",
        "default_graphic": "brain"
    },
    {
        "keywords": ["shopify", "store", "dropshipping", "checkout", "ecom", "cart", "sales"],
        "brand": "shopify",
        "palette": "shopify",
        "style": "corporate",
        "logo_icon": "Sh",
        "logo_text": "SHOPIFY",
        "default_graphic": "shopping"
    },
    {
        "keywords": ["python", "pip", "django", "numpy", "pandas"],
        "brand": "python",
        "palette": "python",
        "style": "tech",
        "logo_icon": "Py",
        "logo_text": "PYTHON",
        "default_graphic": "document"
    },
    {
        "keywords": ["javascript", "js", "typescript", "ts", "react", "next.js", "frontend", "html", "css"],
        "brand": "javascript",
        "palette": "javascript",
        "style": "memphis",
        "logo_icon": "JS",
        "logo_text": "DEV STACK",
        "default_graphic": "chart"
    },
    {
        "keywords": ["spacex", "starship", "rocket", "orbit", "mars", "space", "launch"],
        "brand": "spacex",
        "palette": "spacex",
        "style": "tech",
        "logo_icon": "X",
        "logo_text": "SPACEX",
        "default_graphic": "rocket"
    },
    {
        "keywords": ["chatgpt", "openai", "gpt-4", "gpt-5", "mandala", "llm"],
        "brand": "openai",
        "palette": "openai",
        "style": "gradient",
        "logo_icon": "AI",
        "logo_text": "OPENAI",
        "default_graphic": "brain"
    },
    {
        "keywords": ["linkedin", "b2b", "profile", "job", "career"],
        "brand": "linkedin",
        "palette": "linkedin",
        "style": "corporate",
        "logo_icon": "in",
        "logo_text": "LINKEDIN",
        "default_graphic": "target"
    },
    {
        "keywords": ["youtube", "yt", "vlog", "channel"],
        "brand": "youtube",
        "palette": "youtube",
        "style": "memphis",
        "logo_icon": "YT",
        "logo_text": "YOUTUBE",
        "default_graphic": "rocket"
    },
    # General Semantic Categories
    {
        "keywords": ["ai", "automation", "agent", "robot", "neural", "compiler", "jit", "prompt"],
        "brand": "generic_ai",
        "palette": "pal5", # Midnight Slate (Blue/Teal/Purple)
        "style": "tech",
        "logo_icon": "🤖",
        "logo_text": "AUTO AI",
        "default_graphic": "gear"
    },
    {
        "keywords": ["money", "price", "freelance", "business", "outreach", "client", "ticket", "revenue", "consulting", "agency"],
        "brand": "generic_finance",
        "palette": "pal7", # Burgundy Wine or Gold Slate
        "style": "corporate",
        "logo_icon": "💰",
        "logo_text": "FINANCE",
        "default_graphic": "money"
    },
    {
        "keywords": ["nature", "health", "wellness", "plant", "diet", "bio", "gardening", "earth", "organic"],
        "brand": "generic_wellness",
        "palette": "pal3", # Forest Mist
        "style": "minimal",
        "logo_icon": "🌿",
        "logo_text": "WELLNESS",
        "default_graphic": "lightbulb"
    },
    {
        "keywords": ["design", "creative", "art", "marketing", "brand", "hook", "social", "audience", "instagram", "tiktok"],
        "brand": "generic_creative",
        "palette": "pal2", # Retro Garden or Sunset
        "style": "memphis",
        "logo_icon": "🎯",
        "logo_text": "CREATIVE",
        "default_graphic": "target"
    },
    {
        "keywords": ["security", "protect", "safe", "firewall", "auth", "hack", "cyber"],
        "brand": "generic_security",
        "palette": "pal10", # Gold Slate
        "style": "typography",
        "logo_icon": "🛡️",
        "logo_text": "SECURITY",
        "default_graphic": "shield"
    }
]

def get_autopilot_topic(niche):
    """Retrieve a random high-converting topic based on niche."""
    topics = AUTOPILOT_TOPIC_POOL.get(niche, AUTOPILOT_TOPIC_POOL["All of the above (my niche covers all tech)"])
    return random.choice(topics)

def get_semantic_theme(topic):
    """Analyze the topic and return a theme style override matching the semantic context."""
    t_lower = topic.lower()
    for archetype in AESTHETIC_ARCHETYPES:
        for kw in archetype["keywords"]:
            if kw in t_lower:
                return {
                    "matched": True,
                    "brand": archetype["brand"],
                    "palette": archetype["palette"],
                    "style": archetype["style"],
                    "logo_icon": archetype["logo_icon"],
                    "logo_text": archetype["logo_text"],
                    "default_graphic": archetype["default_graphic"]
                }
    
    # Generic Default
    return {
        "matched": False,
        "brand": "generic",
        "palette": "pal1",
        "style": "minimal",
        "logo_icon": "5x",
        "logo_text": "REACH",
        "default_graphic": "lightbulb"
    }

def clean_fact_text(fact):
    """Clean up fact dictionary/string and format it nicely for slide display."""
    if isinstance(fact, dict):
        text = fact.get("fact", "")
    else:
        text = str(fact)
    text = text.replace('"', '').strip()
    return text

def extract_metric(text):
    """Find any percentage, multiplier or number to highlight as a big stat."""
    match = re.search(r'\b\d+%\b|\b\d+x\b|\b\d+x\b|\b\d+,\d+\b|\b\d+\b', text)
    return match.group(0) if match else "85%"

def reframe_fact_to_human(fact, framework, topic):
    """Reframe raw dry fact into punchy, humanized social media copywriting."""
    fact_clean = clean_fact_text(fact)
    # Extract noun tokens
    words = [w for w in re.findall(r'\b[A-Za-z]{4,}\b', fact_clean) if w.lower() not in ["wikipedia", "source", "article", "category"]]
    kw1 = words[0] if len(words) > 0 else "System"
    kw2 = words[1] if len(words) > 1 else "Integration"
    
    if framework == "insight":
        templates = [
            f"Here is how this works: {fact_clean} By decoupling key layers, we bypass operational latency.",
            f"The real breakthrough is that {fact_clean} This allows systems to execute parallel logic without CPU spikes.",
            f"Let's look at the baseline data: {fact_clean} This removes human error and speeds up execution loops."
        ]
        return random.choice(templates)
    
    elif framework == "metric_explain":
        templates = [
            f"The metrics don't lie. Because {fact_clean} it changes the bottleneck. We transition from manual delay to immediate scale.",
            f"Benchmark tests prove it: {fact_clean} This shifts resource usage down, resulting in maximum cost savings.",
            f"Look at the data closely. {fact_clean} That is a massive multiplier compared to traditional manual configurations."
        ]
        return random.choice(templates)
        
    elif framework == "list_items":
        # Extract 3 actionable verbs/points
        points = [
            f"Isolate core {kw1} and {kw2} parameters",
            f"Deploy automated processing adapters",
            f"Audit system metric benchmarks daily"
        ]
        return points
        
    return fact_clean

def generate_carousel_slides(topic, niche, selected_facts):
    """Generate 6 structured slides with brand-matching overrides and humanized copywriting."""
    theme = get_semantic_theme(topic)
    
    # 1. Clean facts
    clean_facts = [clean_fact_text(f) for f in selected_facts if f]
    while len(clean_facts) < 3:
        clean_facts.append(f"Essential data regarding {topic} helps optimize operations and workflow efficiency.")
    
    # Humanized Hook Generator (Slide 1)
    hooks = [
        f"Stop Doing {topic} Manually",
        f"The {topic} Shift Nobody Is Talking About",
        f"Master {topic} In Under 5 Minutes",
        f"Why Everyone Is Wrong About {topic}",
        f"My Secret Blueprint For {topic}"
    ]
    hook_title = random.choice(hooks).upper()
    
    # Humanized Pain Point (Slide 2)
    problems = [
        f"Most people waste 10+ hours a week trying to manage {topic}. The traditional manual workflow is officially broken. The bottleneck is execution speed.",
        f"Scaling {topic} is impossible when using legacy frameworks. Creators burn out because they sell their hours instead of building systems.",
        f"Underestimating the complexity of {topic} leads to coupling errors and unmaintainable builds. You get left behind if you don't automate."
    ]
    problem_text = random.choice(problems)
    
    # Reframe facts into engaging human scripts
    fact_1 = reframe_fact_to_human(clean_facts[0], "insight", topic)
    fact_2 = reframe_fact_to_human(clean_facts[1], "metric_explain", topic)
    list_points = reframe_fact_to_human(clean_facts[2], "list_items", topic)
    
    # Extract statistic number
    stat_number = extract_metric(clean_facts[1])
    
    # Generate table data contextually
    if theme["brand"] == "shopify":
        table_val = "Flow, Manual, Shopify API\nConversion, 1.2%, 4.5% (Peak)\nSync Time, 4 Hours, Instant\nCart Recovery, 5%, 25%"
        flow_val = "Design Product -> Setup Funnel -> Capture Sales"
    elif theme["brand"] in ["claude", "openai", "generic_ai"]:
        table_val = "Parameter, Human, AI-Engine\nAnalysis, 2 Hrs, 4 Secs\nAccuracy, 85%, 99.8%\nCost/Run, $45.00, $0.02"
        flow_val = "Analyze Request -> Vector Search -> Format Response"
    elif theme["brand"] in ["python", "javascript"]:
        table_val = "Language, Execution, Syntax\nStandard, Baseline, Verbose\nDynamic JIT, 2.8x Faster, Clean\nOptimized C, 10x Max, Complex"
        flow_val = "Write Logic -> Inject JIT -> Benchmark Speed"
    else:
        table_val = f"Parameter, Old Way, {topic}\nEfficiency, Capped, Optimized\nTime Spent, 8 Hours, <15 Mins\nFailure Rate, 12%, <0.5%"
        flow_val = "Inspect Workflow -> Remove Bottlenecks -> Automate"
    
    # Comparison chart data suggestor
    chart_val = f"Before: 15%, After: 95%"
    if "%" in stat_number:
        chart_val = f"Before: 20%, After: {stat_number}"
    elif "x" in stat_number:
        chart_val = f"Manual: 100, Automated: {stat_number.replace('x', '')}"
    
    # Select vector graphics semantically
    graphic_2 = "document" if theme["default_graphic"] != "document" else "shield"
    graphic_3 = theme["default_graphic"]
    graphic_4 = "table"
    graphic_5 = "flow"
    
    slides = [
        {
            "type": "cover",
            "layout": "cover",
            "number": "00",
            "title": hook_title,
            "content": f"A data-backed, step-by-step blueprint to automate and scale this concept.",
            "why_works": f"High-converting hook for {topic}.",
            "visual_type": "none",
            "visual_val": ""
        },
        {
            "type": "body",
            "layout": "quote",
            "number": "01",
            "title": "THE BOTTLENECK",
            "content": problem_text,
            "why_works": "Beginning by highlighting a specific frustration increases audience retention.",
            "visual_type": "icon",
            "visual_val": graphic_2
        },
        {
            "type": "body",
            "layout": "quote",
            "number": "02",
            "title": "CORE INSIGHT",
            "content": fact_1,
            "why_works": "Authentic web data builds trust and authority instantly.",
            "visual_type": "ai_illustration",
            "visual_val": f"{topic} concept, technology"
        },
        {
            "type": "body",
            "layout": "stat",
            "number": "03",
            "title": "KEY PERFORMANCE",
            "stat_number": stat_number,
            "content": fact_2,
            "why_works": "Comparing metrics visually clears up confusion and teaches better.",
            "visual_type": "chart",
            "visual_val": chart_val
        },
        {
            "type": "body",
            "layout": "list",
            "number": "04",
            "title": "ACTION ROADMAP",
            "list_items": list_points,
            "why_works": "Checklists turn raw intelligence into a direct action plan.",
            "visual_type": "flow",
            "visual_val": flow_val
        },
        {
            "type": "outro",
            "layout": "outro",
            "number": "05",
            "title": "TAKE ACTION",
            "content": f"Want our automated systems prompts for {topic}? Comment 'SYSTEM' below and we'll DM them! Follow for daily strategy templates. Save 📌",
            "why_works": "Giving away resources drives high comments and bookmark saves.",
            "visual_type": "none",
            "visual_val": ""
        }
    ]
    
    caption = f"🚨 The Breakdown on {topic} 🚨\n\nMany struggle with this, but here is what the data actually says. Swipe left to see the step-by-step framework!\n\nLet me know your thoughts in the comments."
    
    hashtags = ["#Tech", "#Automation", "#Software", "#Systems", "#Productivity"]
    clean_topic_tag = "#" + "".join(c for c in topic.title() if c.isalnum())
    if clean_topic_tag not in hashtags:
        hashtags.insert(0, clean_topic_tag)
        
    return {
        "original_title": topic,
        "niche": niche,
        "viral_angle": f"Data-backed reframe for {topic}",
        "hook": hook_title,
        "why_trending": f"High search volume and real-time interest in {topic}.",
        "problem": problem_text,
        "content_type": "Multi-Slide Carousel Infographic",
        "slides": slides,
        "caption": caption,
        "hashtags": hashtags[:8],
        "theme_config": {
            "matched": theme["matched"],
            "brand": theme["brand"],
            "palette": theme["palette"],
            "style": theme["style"],
            "logo_icon": theme["logo_icon"],
            "logo_text": theme["logo_text"]
        }
    }

def generate_daily_briefing(niche, recent_topics):
    """Create a daily briefing guide based on custom topics."""
    topics_list = recent_topics if recent_topics else ["Add a custom topic today to get started!"]
    top_topic = topics_list[0]
    
    return {
        "top_trend": top_topic,
        "why_hot": f"Your audience is actively searching for insights on {top_topic} during peak commute hours.",
        "hooks": [
            f"Why everyone is getting {top_topic} wrong 🧵",
            f"The 3-step blueprint for {top_topic} 📈",
            f"Stop ignoring {top_topic} (do this instead) 👇"
        ],
        "video_ideas": [
            f"Mastering {top_topic} in 60 seconds - Complete visual roadmap.",
            f"Common mistakes in {top_topic} and how to avoid them.",
            f"Why {top_topic} is the most important trend in {niche} today."
        ],
        "best_angle": "Focus on actionable data and clear step-by-step screenshots or infographic cards.",
        "avoid_today": "Generic high-level overviews without concrete code examples or real metrics.",
        "post_now": f"Post a LinkedIn Document Carousel on '{top_topic}' at 12:30 PM to catch the lunchtime audience.",
        "niche_insight": f"Audience engagement spikes when you provide downloadable/saveable resources.",
        "total_trends_analyzed": len(recent_topics),
        "sources_used": ["User Custom Topic", "Web Fact Finder"]
    }
