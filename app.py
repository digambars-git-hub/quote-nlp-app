import streamlit as st
import json
import os
from sentence_transformers import SentenceTransformer, util # type: ignore

# Configurable admin credentials
from dotenv import load_dotenv # type: ignore
import os

load_dotenv()  # loads from .env

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

model = load_model()

#List of tags
# Define a rich pool of tags to detect from user input or auto-tag quotes
TAG_POOL = [
    "happiness", "sadness", "peace", "stress", "loneliness", "confidence", "hope", "anger", "grief", "anxiety", "fear", "joy", "contentment",
    "motivation", "discipline", "consistency", "self-control", "focus", "purpose", "ambition", "resilience", "growth", "habits", "mindset",
    "life", "death", "truth", "meaning", "freedom", "destiny", "acceptance", "regret", "change", "choices", "wisdom", "time", "reflection",
    "love", "compassion", "empathy", "friendship", "family", "connection", "kindness", "forgiveness", "trust", "heartbreak",
    "money", "business", "success", "leadership", "risk", "entrepreneurship", "opportunity", "value", "productivity",
    "spirituality", "karma", "consciousness", "mindfulness", "humility", "gratitude", "faith", "ethics", "balance",
    "nature", "simplicity", "beauty", "calm", "environment", "animals", "trees", "seasons", "universe", "earth", "space",
    "lust", "desire", "greed", "addiction", "ego", "materialism", "envy", "jealousy", "temptation"
]

# Load quotes
QUOTES_FILE = "quotes.json"

def load_quotes():
    if not os.path.exists(QUOTES_FILE):
        return []
    with open(QUOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quotes(quotes_data):
    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes_data, f, indent=4, ensure_ascii=False)

quotes_data = load_quotes()
all_tags = TAG_POOL

# Detect relevant moods/tags
def detect_tags(user_input, tag_pool, top_k=3):
    input_emb = model.encode(user_input, convert_to_tensor=True)
    tag_embs = model.encode(tag_pool, convert_to_tensor=True)
    scores = util.cos_sim(input_emb, tag_embs)[0]
    top_indices = scores.argsort(descending=True)[:top_k]
    return [tag_pool[i] for i in top_indices]

# Get top ranked quotes
def get_top_quotes(user_input, selected_tags, top_k=5):
    input_emb = model.encode(user_input, convert_to_tensor=True)
    filtered_quotes = [q for q in quotes_data if any(tag in q["tags"] for tag in selected_tags)]

    if not filtered_quotes:
        return []

    quote_texts = [q["quote"] for q in filtered_quotes]
    quote_embs = model.encode(quote_texts, convert_to_tensor=True)
    semantic_scores = util.cos_sim(input_emb, quote_embs)[0].tolist()

    ranked_quotes = []
    for i, q in enumerate(filtered_quotes):
        overlap = len(set(q["tags"]) & set(selected_tags))
        tag_score = overlap / len(selected_tags)
        final_score = 0.7 * semantic_scores[i] + 0.3 * tag_score
        ranked_quotes.append((final_score, q["quote"]))

    ranked_quotes.sort(reverse=True)
    return [quote for _, quote in ranked_quotes[:top_k]]

# ------------------ STREAMLIT UI ------------------ #

st.title("🧠 Context-Aware Quote Assistant")

# Sidebar for Admin Login
with st.sidebar:
    st.markdown("## 🔐 Admin Portal")
    show_login = st.checkbox("I am the admin")
    is_admin = False

    if show_login:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            st.success("✅ Admin access granted")
            is_admin = True
        else:
            if email or password:
                st.error("❌ Invalid credentials")

# Main interface
st.markdown("Tell me your thoughts, a situation, or emotion. I'll find relevant quotes.")

user_input = st.text_area("💬 What's on your mind?", height=20)

# Optional: show top N quotes
quote_display_count = st.session_state.get("quote_display_count", 5)

if user_input:
    st.markdown("### 🧭 Detected Moods")
    detected = detect_tags(user_input, all_tags, top_k=6)
    st.write(", ".join(detected))

    st.markdown("### ✨ Recommended Quotes")
    top_quotes = get_top_quotes(user_input, detected, top_k=quote_display_count)
    for i, quote in enumerate(top_quotes, 1):
        st.markdown(f"> {i}. *{quote}*")

    if len(top_quotes) == quote_display_count:
        if st.button("🔁 Show More Quotes"):
            st.session_state.quote_display_count = quote_display_count + 5
    else:
        st.info("🎉 All matching quotes shown.")

# Admin quote adder
if is_admin:
    st.markdown("---")
    st.subheader("➕ Add New Quote")

    new_quote = st.text_area("Quote")

    if st.button("Add Quote"):
        if not new_quote.strip():
            st.warning("⚠️ Please enter a quote.")
        else:
            auto_tags = detect_tags(new_quote, all_tags, top_k=6)
            new_entry = {
                "quote": new_quote.strip(),
                "tags": auto_tags
            }
            quotes_data.append(new_entry)
            save_quotes(quotes_data)
            st.success(f"✅ Quote added with tags: {', '.join(auto_tags)}")
