from __future__ import annotations

import json
import os
import random
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()
app = FastAPI(title="Adaptive Assessment Engine API", version="1.0.0")
frontend_origins = os.getenv("FRONTEND_ORIGINS") or os.getenv("FRONTEND_ORIGIN") or "http://localhost:5173,http://localhost:5174"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip().rstrip("/") for origin in frontend_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = None
db = None
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    if os.getenv("MONGODB_URL"):
        client = AsyncIOMotorClient(os.environ["MONGODB_URL"], serverSelectionTimeoutMS=1500)
        db = client[os.getenv("MONGODB_DATABASE", "adaptive_assessment")]
except ImportError:
    pass

memory_assessments: dict[str, dict[str, Any]] = {}
memory_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
THRESHOLDS = {"strong": 80, "developing": 50}
TOPICS = {
    "C": ["Variables & Types", "Control Flow", "Functions", "Arrays", "Pointers", "Strings", "Structures", "Memory"],
    "C++": ["Variables & Types", "Control Flow", "Functions", "Arrays", "Pointers", "OOP", "STL", "Recursion"],
    "Java": ["Variables & Types", "OOP", "Inheritance", "Interfaces", "Collections", "Exceptions", "Strings", "Concurrency"],
    "Python": ["Variables & Types", "Lists & Tuples", "Dictionaries", "Functions", "OOP", "Exceptions", "Modules", "Recursion"],
    "DSA": ["Arrays", "Strings", "Linked Lists", "Stacks & Queues", "Trees", "Graphs", "Searching & Sorting", "Recursion"],
}

# Curated fallback questions ensure a complete demo without an API key.
SEEDS = [
 ("Variables & Types", "Easy", "Which statements about a variable's type are correct?", ["A variable's type determines the kind of value it can represent", "A variable must always use the largest available type", "Some languages infer types from assigned values", "Types can help detect invalid operations"], [0,2,3], "Types describe or constrain the values a variable can hold; some languages infer them and type systems catch invalid operations."),
 ("Control Flow", "Medium", "Which statements about loops are correct?", ["A loop can repeat while a condition remains true", "A for loop must always run at least once", "A break statement can exit a loop", "An infinite loop always terminates automatically"], [0,2], "Loops repeat work and break exits the current loop. A for loop may execute zero times."),
 ("Functions", "Easy", "Which are common properties of functions?", ["They can group reusable behavior", "They can accept input parameters", "Every function must return an integer", "A function can return a value"], [0,1,3], "Functions package reusable behavior and may accept parameters and return values."),
 ("Arrays", "Medium", "Which statements about arrays are generally true?", ["Elements are accessed by index", "Array indexing often starts at zero", "An array can always grow without limit", "Adjacent elements are commonly stored contiguously"], [0,1,3], "Arrays provide indexed access; many languages store their elements contiguously and use zero-based indexing."),
 ("Pointers", "Hard", "Which statements about pointers in C/C++ are correct?", ["A pointer can store an address", "Dereferencing accesses the pointed-to object", "A null pointer refers to a valid object", "Pointer arithmetic depends on the pointed-to type"], [0,1,3], "Pointers hold addresses, dereferencing accesses an object, and arithmetic is scaled by the pointed-to type."),
 ("OOP", "Easy", "Which are core object-oriented programming ideas?", ["Encapsulation", "Inheritance", "Polymorphism", "Compilation"], [0,1,2], "Encapsulation, inheritance, and polymorphism are widely recognized OOP concepts."),
 ("STL", "Medium", "Which statements about the C++ STL are correct?", ["A vector provides dynamic array behavior", "A map stores key-value associations", "An iterator can traverse a container", "Every STL container has constant-time lookup"], [0,1,2], "Vector, map, and iterators are core STL tools; complexity depends on the container and operation."),
 ("Recursion", "Medium", "What helps ensure a recursive function terminates?", ["A reachable base case", "Progress toward that base case", "A recursive call with identical input forever", "A condition that stops further calls"], [0,1,3], "A terminating recursive design reaches a base case, with each call making progress toward it."),
 ("Lists & Tuples", "Easy", "Which statements about Python lists and tuples are true?", ["Lists are mutable", "Tuples are immutable", "Both can contain mixed types", "Tuples are always sorted"], [0,1,2], "Python lists are mutable; tuples are immutable. Either may contain mixed types."),
 ("Dictionaries", "Medium", "Which are true of Python dictionaries?", ["They map keys to values", "Keys must be hashable", "They can contain duplicate keys", "Looking up a key is typically efficient"], [0,1,3], "Dictionaries map unique hashable keys to values and provide efficient average lookup."),
 ("Collections", "Medium", "Which statements about Java collections are correct?", ["List preserves element order", "Set disallows duplicate elements", "Map associates keys with values", "Every collection permits null"], [0,1,2], "Lists, sets, and maps provide different collection semantics; null support depends on implementation."),
 ("Graphs", "Hard", "Which statements about graph traversal are correct?", ["BFS commonly uses a queue", "DFS can be implemented with a stack", "BFS always finds a shortest weighted path", "Visited tracking helps avoid repeated traversal"], [0,1,3], "BFS uses a queue and finds unweighted shortest paths; DFS uses a stack or recursion."),
 ("Searching & Sorting", "Medium", "Which statements are correct?", ["Binary search requires sorted data", "Merge sort has O(n log n) time", "Linear search requires sorted data", "Quick sort has O(n log n) average time"], [0,1,3], "Binary search needs order, merge sort is O(n log n), and quick sort is O(n log n) on average."),
 ("Exceptions", "Easy", "Which statements about exceptions are true?", ["They represent exceptional runtime conditions", "A catch/except block can handle selected errors", "Every exception should always be ignored", "Cleanup may be placed in a finally block"], [0,1,3], "Exception handlers can recover or report failures, and finally blocks commonly perform cleanup."),
 ("Strings", "Easy", "Which statements about strings are commonly true?", ["Strings represent text", "Some languages make strings immutable", "String indexing is identical in every language", "Concatenation combines strings"], [0,1,3], "Strings represent text and can be concatenated; mutability and indexing details vary by language."),
 ("Trees", "Medium", "Which statements about binary trees are correct?", ["A node has at most two children", "An inorder traversal of a BST yields sorted keys", "Every binary tree is balanced", "A leaf has no children"], [0,1,3], "Binary tree nodes have at most two children; BST inorder traversal is sorted and leaves have none."),
 ("Stacks & Queues", "Easy", "Which statements are correct?", ["A stack is last-in, first-out", "A queue is first-in, first-out", "A stack's standard removal operation is dequeue", "Queues are useful for breadth-first traversal"], [0,1,3], "Stacks use LIFO and queues use FIFO; queues support breadth-first traversal."),
 ("Linked Lists", "Medium", "Which are properties of a singly linked list?", ["Nodes link to a next node", "Random access is typically O(1)", "Insertion near a known node can be O(1)", "The final node often points to null"], [0,2,3], "A singly linked list follows next links, making random access linear but local insertion constant time."),
 ("Memory", "Hard", "Which practices help avoid memory errors in C/C++?", ["Release dynamically allocated memory when done", "Use a pointer only while its object is alive", "Dereference uninitialized pointers", "Check allocation results where required"], [0,1,3], "Correct lifetime management and valid pointers help prevent leaks and undefined behavior."),
 ("Interfaces", "Medium", "Which are true about Java interfaces?", ["They define a contract a class can implement", "A class may implement multiple interfaces", "They can contain default methods", "They can be instantiated directly"], [0,1,2], "Java interfaces define contracts, can have default methods, and a class can implement several."),
 ("Concurrency", "Hard", "Which practices can help with thread safety?", ["Protect shared mutable state", "Use immutable data where practical", "Assume thread scheduling is deterministic", "Use suitable concurrent utilities"], [0,1,3], "Synchronization, immutability, and concurrency primitives help coordinate shared state."),
]

class StartRequest(BaseModel):
    user_id: str = "demo-user"
    subject: str
    question_count: int = Field(default=40, ge=1, le=40)
    focus_topic: str | None = None

class AnswerRequest(BaseModel):
    assessment_id: str
    question_id: str
    selected_answers: list[int] = []

class HintRequest(BaseModel):
    assessment_id: str
    question_id: str
    selected_answers: list[int] = []

def public_question(q: dict[str, Any]) -> dict[str, Any]:
    return {k: q[k] for k in ("question_id", "subject", "topic", "difficulty", "question", "options", "hint") if k in q}

def topic_bank(subject: str, focus: str | None = None) -> list[str]:
    if subject not in TOPICS:
        raise HTTPException(422, "Choose a supported subject")
    return [focus] if focus else TOPICS[subject]

def demo_question(subject: str, topic: str, index: int, difficulty: str) -> dict[str, Any]:
    matches = [s for s in SEEDS if s[0] == topic]
    seed = matches[index % len(matches)] if matches else SEEDS[index % len(SEEDS)]
    # Rotate curated templates and vary prompt framing while retaining verified answer keys.
    prompts = [seed[2], f"Select every correct statement: {seed[2]}", f"For {topic.lower()}, {seed[2][0].lower() + seed[2][1:]}"]
    return {"question_id": f"{subject.lower().replace('+','p')}_{uuid.uuid4().hex[:10]}", "subject": subject, "topic": topic, "difficulty": difficulty, "question": prompts[index % len(prompts)], "options": list(seed[3]), "correct_answers": list(seed[4]), "explanation": seed[5], "hint": "Evaluate each statement independently, then choose the complete set that is correct.", "fingerprint": {"topic": topic, "concept": seed[2][:60], "pattern": "concept check"}}

async def generate_questions(subject: str, topics: list[str], count: int, history: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pool = []
        for i in range(count):
            topic = topics[i % len(topics)]
            difficulty = ["Easy", "Medium", "Hard"][min(2, i // max(1, count // 3))]
            pool.append(demo_question(subject, topic, i, difficulty))
        return pool, True
    from openai import AsyncOpenAI
    ai = AsyncOpenAI(api_key=api_key)
    history_text = json.dumps([{"topic": h.get("topic"), "fingerprint": h.get("fingerprint"), "question": h.get("question")} for h in history[-300:]])[:14000]
    prompt = f'''Create exactly {count} unique multiple-select questions for {subject}. Cover these topics evenly: {topics}. Every question must have 4 options and 1-3 correct_answers as zero-based indices. Vary difficulty Easy/Medium/Hard. Avoid concepts/questions in this history: {history_text}. Return ONLY valid JSON with key "questions", each containing topic,difficulty,question,options,correct_answers,explanation,hint,fingerprint (concept and pattern). Do not include markdown.'''
    try:
        response = await ai.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"), response_format={"type": "json_object"}, messages=[{"role": "system", "content": "You create accurate programming assessments. Return valid JSON only."}, {"role": "user", "content": prompt}], temperature=0.8)
        data = json.loads(response.choices[0].message.content or "{}")
        questions = data.get("questions", [])
        if len(questions) != count:
            raise ValueError("Incorrect question count")
        normalized = []
        for i, q in enumerate(questions):
            if not q.get("question") or len(q.get("options", [])) != 4 or not q.get("correct_answers"):
                raise ValueError("Invalid question schema")
            q.update(question_id=f"{subject.lower().replace('+','p')}_{uuid.uuid4().hex[:10]}", subject=subject, topic=q.get("topic", topics[i % len(topics)]), difficulty=q.get("difficulty", "Medium"))
            normalized.append(q)
        return normalized, False
    except Exception as exc:
        raise HTTPException(502, f"AI question generation failed: {exc}")

async def get_history(user_id: str) -> list[dict[str, Any]]:
    if db is not None:
        try:
            return await db.questions.find({"user_id": user_id}, {"_id": 0}).to_list(length=1000)
        except Exception:
            pass
    return memory_history[user_id]

async def persist_assessment(doc: dict[str, Any]):
    if db is not None:
        try:
            await db.assessments.replace_one({"assessment_id": doc["assessment_id"]}, doc.copy(), upsert=True)
            return
        except Exception:
            pass
    memory_assessments[doc["assessment_id"]] = doc

async def load_assessment(aid: str) -> dict[str, Any]:
    doc = memory_assessments.get(aid)
    if doc is None and db is not None:
        doc = await db.assessments.find_one({"assessment_id": aid}, {"_id": 0})
    if doc is None:
        raise HTTPException(404, "Assessment not found")
    return doc

@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "ai" if os.getenv("OPENAI_API_KEY") else "demo", "database": "mongodb" if db is not None else "memory"}

@app.post("/api/assessment/start")
async def start_assessment(req: StartRequest):
    topics = topic_bank(req.subject, req.focus_topic)
    history = await get_history(req.user_id)
    questions, demo = await generate_questions(req.subject, topics, req.question_count, history)
    aid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {"assessment_id": aid, "user_id": req.user_id, "subject": req.subject, "total_questions": len(questions), "started_at": now, "completed_at": None, "questions": questions, "answers": {}, "demo_mode": demo}
    await persist_assessment(doc)
    # Keep fingerprints locally even without MongoDB, so repeat demo sessions can avoid the same concepts.
    memory_history[req.user_id].extend({"topic": q["topic"], "question": q["question"], "fingerprint": q.get("fingerprint", {})} for q in questions)
    return {"assessment_id": aid, "first_question": public_question(questions[0]), "question_count": len(questions), "demo_mode": demo, "mode_label": "Demo question bank" if demo else "AI generated"}

@app.post("/api/assessment/answer")
async def save_answer(req: AnswerRequest):
    a = await load_assessment(req.assessment_id)
    idx = next((i for i, q in enumerate(a["questions"]) if q["question_id"] == req.question_id), None)
    if idx is None:
        raise HTTPException(404, "Question does not belong to this assessment")
    q = a["questions"][idx]
    selected = sorted(set(req.selected_answers))
    if any(i < 0 or i >= len(q["options"]) for i in selected):
        raise HTTPException(422, "Selected option index is invalid")
    correct = selected == sorted(q["correct_answers"])
    a["answers"][req.question_id] = {"selected_answers": selected, "correct": correct, "answered_at": datetime.now(timezone.utc).isoformat()}
    if db is not None:
        await db.assessments.update_one({"assessment_id": a["assessment_id"]}, {"$set": {f"answers.{req.question_id}": a["answers"][req.question_id]}})
        await db.questions.insert_one({"user_id": a["user_id"], "assessment_id": a["assessment_id"], "question_id": q["question_id"], "subject": q["subject"], "topic": q["topic"], "question": q["question"], "fingerprint": q.get("fingerprint", {}), "created_at": datetime.now(timezone.utc).isoformat()})
    next_idx = idx + 1
    result = {"saved": True, "is_last": next_idx >= len(a["questions"]), "answered_count": len(a["answers"])}
    if next_idx < len(a["questions"]):
        levels = ["Easy", "Medium", "Hard"]
        current_level = levels.index(q["difficulty"]) if q["difficulty"] in levels else 1
        next_level = max(0, min(2, current_level + (1 if correct else -1)))
        a["questions"][next_idx]["difficulty"] = levels[next_level]
        if db is not None:
            await db.assessments.update_one({"assessment_id": a["assessment_id"]}, {"$set": {"questions": a["questions"]}})
        result["next_question"] = public_question(a["questions"][next_idx])
    if next_idx >= len(a["questions"]):
        a["completed_at"] = datetime.now(timezone.utc).isoformat()
        await persist_assessment(a)
    return result

@app.post("/api/assessment/hint")
async def get_hint(req: HintRequest):
    a = await load_assessment(req.assessment_id)
    q = next((q for q in a["questions"] if q["question_id"] == req.question_id), None)
    if q is None: raise HTTPException(404, "Question not found")
    hint = q.get("hint")
    if os.getenv("OPENAI_API_KEY"):
        from openai import AsyncOpenAI
        ai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = await ai.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"), messages=[{"role":"system","content":"Give one concise hint without revealing the answer."},{"role":"user","content":q["question"]}], max_tokens=100)
        hint = response.choices[0].message.content or hint
    return {"hint": hint}

@app.get("/api/assessment/result/{assessment_id}")
async def result(assessment_id: str):
    a = await load_assessment(assessment_id)
    if len(a["answers"]) < len(a["questions"]):
        raise HTTPException(409, "Assessment is not complete")
    topic_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    difficulty_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    wrong = []
    score = 0
    for q in a["questions"]:
        ans = a["answers"][q["question_id"]]
        stat = topic_stats[q["topic"]]; stat["total"] += 1
        ds = difficulty_stats[q["difficulty"]]; ds["total"] += 1
        if ans["correct"]:
            score += 1; stat["correct"] += 1; ds["correct"] += 1
        else:
            wrong.append({"question_id": q["question_id"], "question": q["question"], "topic": q["topic"], "difficulty": q["difficulty"], "options": q["options"], "selected_answers": ans["selected_answers"], "correct_answers": q["correct_answers"], "explanation": q["explanation"]})
    summary = {topic: {**v, "accuracy": round(100*v["correct"]/v["total"])} for topic,v in topic_stats.items()}
    strong = [t for t,v in summary.items() if v["accuracy"] >= THRESHOLDS["strong"]]
    weak = [t for t,v in summary.items() if v["accuracy"] < THRESHOLDS["developing"]]
    overall = round(100*score/len(a["questions"]))
    comp = "Advanced" if overall >= 80 else "Intermediate" if overall >= 50 else "Building foundations"
    difficulty = {k: {**v, "accuracy": round(100*v["correct"]/v["total"]) if v["total"] else 0} for k,v in difficulty_stats.items()}
    return {"assessment_id": assessment_id, "subject": a["subject"], "score": score, "correct": score, "incorrect": len(a["questions"])-score, "total": len(a["questions"]), "accuracy": overall, "competency": comp, "topic_summary": summary, "difficulty_summary": difficulty, "weak_topics": weak, "strong_topics": strong, "wrong_questions": wrong, "demo_mode": a["demo_mode"], "thresholds": THRESHOLDS}

class SummaryRequest(BaseModel):
    result: dict[str, Any]

@app.post("/api/assessment/ai-summary")
async def ai_summary(req: SummaryRequest):
    data = req.result
    if not os.getenv("OPENAI_API_KEY"):
        strong = ", ".join(data.get("strong_topics", [])) or "no clear strong topic yet"
        weakest = min(data.get("topic_summary", {}).items(), key=lambda x: x[1]["accuracy"], default=None)
        weakline = f"Your lowest topic was {weakest[0]} ({weakest[1]['accuracy']}%)." if weakest else "Complete more topic questions to reveal a focused practice area."
        return {"summary": f"You scored {data.get('score', 0)} of {data.get('total', 0)} ({data.get('accuracy', 0)}%). Your strongest topics were {strong}. {weakline} Review the explanations for missed questions, then practice your lowest scoring topic." , "demo_mode": True}
    from openai import AsyncOpenAI
    ai = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = await ai.chat.completions.create(model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"), response_format={"type":"json_object"}, messages=[{"role":"system","content":"Write a concise, supportive assessment summary grounded only in supplied data. Do not invent diagnoses or facts. Return JSON {summary:string}."},{"role":"user","content":json.dumps(data)}], max_tokens=250)
    return {**json.loads(response.choices[0].message.content or "{}"), "demo_mode": False}

@app.get("/api/progress/{user_id}")
async def progress(user_id: str):
    if db is None: return {"assessments": []}
    docs = await db.assessments.find({"user_id": user_id, "completed_at": {"$ne": None}}, {"_id": 0, "questions": 0, "answers": 0}).sort("completed_at", 1).to_list(length=100)
    return {"assessments": docs}
