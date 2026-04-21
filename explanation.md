# ShieldGuard System Architecture: From ML to AI Agents

Welcome! This document explains how ShieldGuard works behind the scenes in plain English. Specifically, it details the journey of a phone call transcript: how it gets processed by our trained Machine Learning (ML) models, and how those results are passed to our specialized AI Agents to determine if the call is a dangerous "vishing" (voice phishing) scam.

---

## 1. The Starting Point: The ML Model (Phase 1)
When a phone call transcript enters the system, it first goes through our specialized ML layer. Think of this as our "fast-acting radar."
* **Prediction:** The transcript is analyzed by a trained ML model (like Support Vector Machine or a Neural Network). 
* **Scoring:** The ML model assigns a **confidence score** (from 0 to 100%) and a label: `"vishing"` or `"safe"`.
* **Clues (Keywords & Phrases):** Along with the score, the system extracts the exact words (TF-IDF keywords) and phrases (regex patterns) that triggered the alarm—like *"account suspended"* or *"urgent action required"*.

## 2. The Threshold Gate: Do we need a deeper look?
We don't need a deep investigation for every single call. To be efficient, ShieldGuard uses a **Threshold Gate**.
* If the ML score is very low (e.g., `< 0.45`), the system accepts the ML's verdict as `"safe"` and skips the advanced AI analysis. 
* If the ML score is high or suspicious, the system flags the transcript for a deeper, more sophisticated review by our AI agents.

## 3. Gathering Evidence (RAG Lookup)
Before the AI agents start their investigation, they need context. The system searches a database of past scams to find **similar historical cases**. This process is called Retrieval-Augmented Generation (RAG). By giving our AI real-world examples of similar attacks, it becomes much smarter and more accurate.

## 4. The Case File is Built
An automated "Case File" is packaged up and handed over to the AI Agents. This file contains:
* The original transcript text
* The ML score and label
* The flagged suspicious keywords and phrases
* The similar past cases found from the database

## 5. The AI Investigation Crew (Phase 2)
ShieldGuard uses a team of four specialized AI Agents (powered by CrewAI and a Large Language Model) that work together to analyze the case file. Think of them as a team of detectives:

1. **Technical Auditor(Agent A):** Looks at the ML model's work. It checks if the alarm was justified, ensuring the ML model didn't just spot a scary keyword purely out of context.
2. **Pattern Detective(Agent B):** Compares the transcript against the historical scam cases to figure out exactly what *type* of scam this is (e.g., "Bank Impersonation," "Tech Support Scam").
3. **Psychology Profiler(Agent C):** Analyzes the psychological tactics being used against the victim. It looks for manipulation techniques like *Urgency*, *Authority*, or *Fear*.
4. **Safety Guardian(Agent D):** The team lead. It gathers all the findings from the other three detectives and writes a simple, jargon-free final verdict and explanation that is easy for anyone to understand. It also provides step-by-step actions for the user to stay safe.

## 6. The Final Cross-Check
Right before showing the results to the user, ShieldGuard performs a "Sanity Check" between the original ML model and the AI Agents:
* Do they agree? Great!
* Do they strongly disagree? (For instance, the ML model says it's a dangerous scam, but the AI agents think it's perfectly safe). If there's a serious conflict, the system plays it safe and flags the call as **"SUSPICIOUS — UNCONFIRMED"**.

## Summary Flowchart
**Transcript** ➔ **ML Model** *(finds keywords & generates score)* ➔ **Database** *(finds past similar scams)* ➔ **AI Detective Crew** *(validates, profiles, and explains)* ➔ **Final Human-Friendly Report**
