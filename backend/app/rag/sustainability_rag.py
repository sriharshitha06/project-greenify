import os
import json
import numpy as np
import requests
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SustainabilityRAG:
    def __init__(self):
        self.tips_path = os.path.join(os.path.dirname(__file__), "sustainability_tips.json")
        self.tips = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tips_vectors = None
        self.load_tips()
        self.initialize_vector_store()

    def load_tips(self):
        try:
            if os.path.exists(self.tips_path):
                with open(self.tips_path, "r") as f:
                    self.tips = json.load(f)
            else:
                self.tips = []
                print("Sustainability tips database not found.")
        except Exception as e:
            print(f"Error loading sustainability tips: {e}")
            self.tips = []

    def initialize_vector_store(self):
        if not self.tips:
            return
        
        # Combine title and description for vector representation
        corpus = [f"{tip['category']} {tip['title']} {tip['description']}" for tip in self.tips]
        try:
            self.tips_vectors = self.vectorizer.fit_transform(corpus)
        except Exception as e:
            print(f"Error vectorizing tips: {e}")

    def query_vector_store(self, query_text: str, top_k: int = 3) -> list:
        if not self.tips or self.tips_vectors is None:
            return []
            
        try:
            query_vector = self.vectorizer.transform([query_text])
            similarities = cosine_similarity(query_vector, self.tips_vectors).flatten()
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            matched_tips = []
            for idx in top_indices:
                # Include similarity score
                tip = self.tips[idx].copy()
                tip['similarity'] = float(similarities[idx])
                matched_tips.append(tip)
            return matched_tips
        except Exception as e:
            print(f"Error searching vector store: {e}")
            # Fallback: slice top k
            return self.tips[:top_k]

    def generate_recommendations(self, user_name: str, activity_log: dict, query_text: Optional[str] = None) -> dict:
        """
        Runs RAG:
        1. Identifies highest carbon emitting categories from user log.
        2. Queries the vector store for matching tips.
        3. Invokes real LLM if API keys are available, otherwise falls back to a realistic local advisor.
        """
        # Determine highest emission category
        categories_co2 = {
            "energy": (activity_log.get('electricity_kwh', 0.0) * 0.62) + (activity_log.get('lpg_cylinders', 0.0) * 24.4),
            "transport": (activity_log.get('petrol_liters', 0.0) * 2.35) + (activity_log.get('diesel_liters', 0.0) * 2.68) + (activity_log.get('cng_liters', 0.0) * 2.50) + (activity_log.get('public_transport_km', 0.0) * 0.08),
            "diet": 2.0 if activity_log.get('diet_type') == 'vegan' else (3.5 if activity_log.get('diet_type') == 'vegetarian' else 7.0),
            "waste": 1.5 * (1.0 - activity_log.get('waste_recycled_pct', 0.0) / 100.0)
        }
        
        highest_cat = max(categories_co2, key=categories_co2.get)
        total_co2 = sum(categories_co2.values())
        
        # Build vector search query
        search_query = query_text if query_text else f"reduce carbon footprint high {highest_cat} emissions and optimize eco lifestyle"
        
        # Vector search
        matched_tips = self.query_vector_store(search_query, top_k=3)
        
        # Construct advice report
        advice_text = self.generate_llm_advice(user_name, total_co2, categories_co2, highest_cat, matched_tips, query_text)
        
        return {
            "recommendations": matched_tips,
            "advice": advice_text
        }

    def generate_llm_advice(self, user_name: str, total_co2: float, categories_co2: dict, highest_cat: str, matched_tips: list, query_text: Optional[str]) -> str:
        # Check environment keys for real LLM integration
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        prompt = f"""
        User Name: {user_name}
        Total Daily Footprint: {total_co2:.2f} kg CO2e
        Breakdown:
        - Energy: {categories_co2['energy']:.2f} kg CO2e
        - Transport: {categories_co2['transport']:.2f} kg CO2e
        - Diet: {categories_co2['diet']:.2f} kg CO2e
        - Waste: {categories_co2['waste']:.2f} kg CO2e
        Highest Source of Emissions: {highest_cat.upper()}
        User Query: {query_text or 'Give me a general carbon reduction advice report.'}
        
        Relevant Sustainability Recommendations Retrieved:
        1. {matched_tips[0]['title']} ({matched_tips[0]['category']}): {matched_tips[0]['description']} Impact: {matched_tips[0]['impact']}
        2. {matched_tips[1]['title']} ({matched_tips[1]['category']}): {matched_tips[1]['description']} Impact: {matched_tips[1]['impact']}
        3. {matched_tips[2]['title']} ({matched_tips[2]['category']}): {matched_tips[2]['description']} Impact: {matched_tips[2]['impact']}
        
        Write a professional, encouraging, and detailed markdown-formatted sustainability advisor report. Address the user by name, analyze their carbon footprint breakdown, and explain how they can implement these specific recommendations to make a major impact. Explain why {highest_cat.upper()} is their primary area of focus.
        """
        
        if gemini_key:
            try:
                # Call Gemini API
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_key}"
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": prompt}]}]}
                r = requests.post(url, headers=headers, json=data, timeout=10)
                if r.status_code == 200:
                    res = r.json()
                    return res['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                print(f"Gemini API error: {e}. Reverting to local simulator.")
                
        elif openai_key:
            try:
                # Call OpenAI API
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                }
                data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a professional environmental scientist and sustainability coach."},
                        {"role": "user", "content": prompt}
                    ]
                }
                r = requests.post(url, headers=headers, json=data, timeout=10)
                if r.status_code == 200:
                    res = r.json()
                    return res['choices'][0]['message']['content']
            except Exception as e:
                print(f"OpenAI API error: {e}. Reverting to local simulator.")

        # Fallback Local Generator: Simulates the LLM output with a beautiful customized markdown template
        return self.generate_local_fallback_advice(user_name, total_co2, categories_co2, highest_cat, matched_tips, query_text)

    def generate_local_fallback_advice(self, user_name: str, total_co2: float, categories_co2: dict, highest_cat: str, matched_tips: list, query_text: Optional[str]) -> str:
        query_clause = f"Regarding your request: *\"{query_text}\"*," if query_text else "Based on your lifestyle logging patterns,"
        
        adv = f"## 🍃 Personal Eco-Advisor Report for **{user_name}**\n\n"
        adv += f"Hello {user_name}! I have analyzed your carbon footprint tracking logs to compile this personalized advisor report. "
        adv += f"{query_clause} here is an analysis of your daily ecological impact and actionable recommendations.\n\n"
        
        adv += "### 📊 Carbon Footprint Analysis\n"
        adv += f"Your current calculated carbon footprint is **{total_co2:.2f} kg CO2e / day**. Here is how your daily emissions are distributed:\n\n"
        
        # Add visual bar chart simulation in Markdown
        for cat, val in categories_co2.items():
            pct = (val / total_co2 * 100) if total_co2 > 0 else 0
            bars = "🟩" * int(pct / 10)
            if not bars and pct > 0:
                bars = "🟩"
            adv += f"- **{cat.capitalize()}**: {val:.2f} kg CO2e ({pct:.1f}%) {bars}\n"
            
        adv += f"\n> [!WARNING]\n"
        adv += f"> **Primary Focus Area**: Your largest source of carbon emissions comes from **{highest_cat.upper()}** ({categories_co2[highest_cat]:.2f} kg CO2e). Concentrating on reducing emissions in this category will yield the highest visual reduction in your environmental footprint.\n\n"
        
        adv += "### 💡 Tailored Recommendations (RAG Matches)\n"
        adv += "Using semantic vector search against our sustainability catalog, I have identified the top 3 high-impact actions for you:\n\n"
        
        for i, tip in enumerate(matched_tips, 1):
            adv += f"#### {i}. {tip['title']} (`{tip['category'].upper()}`)\n"
            adv += f"* **What to do**: {tip['description']}\n"
            adv += f"* **Expected Impact**: {tip['impact']}\n"
            
            # Custom reasoning based on user logs
            if tip['category'] == 'energy' and categories_co2['energy'] > 5.0:
                adv += f"* **Why this helps you**: Your energy sector emits {categories_co2['energy']:.2f} kg CO2e daily. Lowering home electrical grid loads directly decreases this value.\n"
            elif tip['category'] == 'transport' and categories_co2['transport'] > 5.0:
                adv += f"* **Why this helps you**: Commuting comprises a major chunk of your emissions. Offsetting petrol/diesel trips with this tip immediately drops your footprint.\n"
            elif tip['category'] == 'diet' and categories_co2['diet'] > 3.0:
                adv += f"* **Why this helps you**: Food choice is a quick lever. Transitioning food habits reduces agriculture-associated emissions significantly.\n"
            elif tip['category'] == 'waste':
                adv += f"* **Why this helps you**: Recycling and composting diverts biodegradable and chemical waste from landfills, curbing methane output.\n"
            
            adv += "\n"
            
        adv += "### 🏆 Weekly Sustainability Action Plan\n"
        adv += "1. **Implement the targets**: Commit to just one of the matched actions above for the next 7 days.\n"
        adv += "2. **Verify actions**: Take a picture of your eco-friendly activities (cycling to work, using a reusable water bottle) and upload them under the **Eco-Verify** section to unlock badge achievements and climb the leaderboard!\n"
        adv += "3. **Track changes**: Keep logging your daily stats to see your carbon graph trend downwards.\n\n"
        adv += "*\"Small actions, when multiplied by millions of people, can transform the world.\" Keep going!* 🌍"
        
        return adv

# Instantiate a single global RAG engine
rag_advisor = SustainabilityRAG()
