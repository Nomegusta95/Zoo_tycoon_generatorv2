import tkinter as tk
from tkinter import ttk, messagebox

from data_loader import load_animals
from generator import generate_game
import random
from project_rewards import get_project_reward
from best_project import generate_best_project
from unlock_requirement_debugger import analyze_high_tier_animals
from predefined_projects import build_predefined_projects

# --- LOAD DATA ---
animals = load_animals("animals.xlsx")


# --- HELPERS ---
def extract_names(project):
    names = set()

    for entry in project["animals"]:
        parts = entry.split(" OR ")

        for p in parts:
            tokens = p.split()

            if tokens and tokens[-1].isdigit():
                tokens = tokens[:-1]

            name = " ".join(tokens)
            names.add(name)

    return names

def get_lvl3_animals(project):
    names = set()
    for entry in project["animals"]:
        parts = entry.split(" OR ")
        for p in parts:
            name = " ".join(p.split()[:-1]) if p.split()[-1].isdigit() else p
            names.add(name)
    return names
def group_animals(game_animals):
    lvl1 = []
    lvl2 = []
    lvl3 = []
    special = []
    habitats = set()

    for a in game_animals:
        if a["type"] == "main":
            if a["level"] == 1:
                lvl1.append(a["name"])
            elif a["level"] == 2:
                lvl2.append(a["name"])
            elif a["level"] == 3:
                lvl3.append(a["name"])

        if a.get("special"):
            special.append(a["name"])

        for h in a.get("habitats", []):
            habitats.add(h)

    return lvl1, lvl2, lvl3, special, sorted(habitats)


# --- GUI APP ---

class ZooApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Zoo Generator")

        # --- LEFT: ANIMAL SELECTION ---
        left_frame = tk.Frame(root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        tk.Label(left_frame, text="Select Animals (required)").pack()

        # --- LISTBOX + SCROLL ---
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            width=35,
            height=25,
            yscrollcommand=scrollbar.set
        )

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # --- BUILD LEVEL GROUPS ---
        lvl1 = [a for a in animals if a["type"] == "main" and a["level"] == 1]
        lvl2 = [a for a in animals if a["type"] == "main" and a["level"] == 2]
        lvl3 = [a for a in animals if a["type"] == "main" and a["level"] == 3]

        def insert_group(title, group):
            self.listbox.insert(tk.END, f"--- {title} ---")
            self.listbox.itemconfig(tk.END, fg="gray")

            for a in sorted(group, key=lambda x: x["name"]):
                name = a["name"]

                if a.get("special"):
                    name = f"⭐ {name}"

                self.listbox.insert(tk.END, name)

                if a.get("special"):
                    self.listbox.itemconfig(tk.END, fg="darkorange")

        insert_group("LEVEL 1", lvl1)
        insert_group("LEVEL 2", lvl2)
        insert_group("LEVEL 3", lvl3)

        tk.Button(left_frame, text="Generate Game", command=self.generate).pack(pady=10)

        # --- RIGHT: OUTPUT ---
        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.project_frames = []
        self.project_texts = []

        for i in range(5):
            frame = tk.LabelFrame(right_frame, text=f"Project {i+1}", padx=5, pady=5)
            frame.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")

            text = tk.Text(frame, height=8, width=40)
            text.pack()

            self.project_frames.append(frame)
            self.project_texts.append(text)

        self.summary = tk.Text(right_frame, height=10)
        self.summary.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)


    def generate(self):
        usage = {}
        selected_indices = self.listbox.curselection()

        required = []
        for i in selected_indices:
            value = self.listbox.get(i)

            if value.startswith("---"):
                continue

            value = value.replace("⭐ ", "")
            required.append(value)

        try:
            # --- GENERATE GAME POOL ---
            game_pool, game_animals = generate_game(animals, required)
            analyze_high_tier_animals(game_animals)
            # --- GENERATE PROJECTS ---

            lookup = {a["name"]: a for a in game_animals}

            mandatory_projects, optional_projects = build_predefined_projects(game_animals, lookup)

            # --- PREPARE MANDATORY ---
            mandatory_projects.sort(key=lambda p: p["difficulty"], reverse=True)

            if len(mandatory_projects) > 5:
                mandatory_projects = mandatory_projects[:5]

            game = []
            used_lvl3 = set()

            lvl3_project_count = 0
            special_project_count = 0

            for p in mandatory_projects:

                if len(game) >= 5:
                    break

                names = extract_names(p)

                if any(usage.get(name, 0) >= 2 for name in names):
                    continue

                game.append(p)

                # --- UPDATE GLOBAL STATE ---
                p_lvl3 = {
                    name for name in names
                    if lookup.get(name, {}).get("level") == 3
                }

                p_special = any(
                    lookup.get(name, {}).get("special")
                    for name in names
                )

                if p_lvl3:
                    lvl3_project_count += 1

                if p_special:
                    special_project_count += 1

                used_lvl3.update(p_lvl3)

            target_tiers = ["easy", "hard"]
            target_tiers += ["medium"] * (5 - len(target_tiers))
            random.shuffle(target_tiers)

            # --- GENERATE REST ---
            remaining_slots = 5 - len(game)

            lvl3_project_count = 0
            special_project_count = 0

            for target_tier in target_tiers[:remaining_slots]:

                best_candidate = None
                best_score = -999
                attempts = 0

                while attempts < 50:
                    candidates = []

                    # --- predefined (controlled chance) ---
                    if optional_projects and random.random() < 0.4:
                        candidates.extend(optional_projects)


                    # --- generated ---
                    for _ in range(5):
                        p = generate_best_project(
                            game_animals,
                            usage,
                            previous_projects=game,
                            attempts=5
                        )
                        if p:
                            candidates.append(p)

                    if not candidates:
                        attempts += 1
                        continue

                    p = random.choice(candidates)

                    # --- validate usage ---
                    names = extract_names(p)

                    if any(usage.get(name, 0) >= 2 for name in names):
                        attempts += 1
                        continue

                    score = 0

                    # --- TIER MATCH (soft, not required) ---
                    if p["tier"] == target_tier:
                        score += 3
                    else:
                        score -= 2

                    # --- LVL3 GLOBAL FILTER (soft) ---
                    p_lvl3 = {
                        name for name in get_lvl3_animals(p)
                        if any(a["name"] == name and a["level"] == 3 for a in game_animals)
                    }
                    # --- DETECT SPECIAL ---
                    names = extract_names(p)

                    p_special = any(
                        a["name"] in names and a.get("special")
                        for a in game_animals
                    )
                    # --- LVL3 GLOBAL CONTROL (SMART BIAS) ---
                    if p_lvl3:
                        if lvl3_project_count >= 2:
                            score -= 5  # soft penalty
                        else:
                            score += 2

                        # avoid repeating same lvl3 animals
                        if any(name in used_lvl3 for name in p_lvl3):
                            score -= 3

                    # --- SPECIAL GLOBAL CONTROL (HARD LIMIT) ---
                    if p_special:
                        if special_project_count >= 1:
                            score -= 100  # hard block
                        else:
                            score += 3

                    # keep best candidate even if imperfect
                    if score > best_score:
                        best_score = score
                        best_candidate = (p, p_lvl3, p_special)

                    attempts += 1

                # --- accept best found ---
                if best_candidate:
                    p, p_lvl3, p_special = best_candidate

                    if p_lvl3:
                        lvl3_project_count += 1

                    if p_special:
                        special_project_count += 1

                    used_lvl3.update(p_lvl3)
                    game.append(p)
                else:
                    game.append({
                        "name": "Failed Project",
                        "animals": [],
                        "theme": "None",
                        "theme_type": "none",
                        "difficulty": 0
                    })

            # fallback safety
            while len(game) < 5:
                game.append({
                    "name": "Failed Project",
                    "animals": [],
                    "theme": "None",
                    "theme_type": "none",
                    "difficulty": 0
                })

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        # --- PROJECTS ---
        for i, p in enumerate(game):

            frame = self.project_frames[i]
            text = self.project_texts[i]

            # ✅ NAME IN TITLE
            frame.config(text=f"Project {i+1}: {p.get('name', 'Unnamed')}")

            text.delete("1.0", tk.END)

            text.insert(tk.END, f"{p.get('theme_type', 'unknown')} - {p.get('theme', 'unknown')}\n")
            reward = get_project_reward(p, lookup)

            if reward["first"] <= 5:
                tier = "easy"
            elif reward["first"] <= 9:
                tier = "medium"
            else:
                tier = "hard"

            if p["animals"]:
                text.insert(tk.END, f"Animals: {len(p['animals'])}\n")
            else:
                text.insert(tk.END, "⚠ Failed to generate\n")
            text.insert(tk.END, f"Reward:\n")
            text.insert(tk.END, f"  🥇 First: {reward['first']}\n")
            text.insert(tk.END, f"  🥈 Second: {reward['second']}\n")

            text.insert(tk.END, f"\nDifficulty: {round(p['difficulty'], 1)} ({tier})\n\n")

            for a in p["animals"]:
                text.insert(tk.END, f"- {a}\n")

        # --- CLEAR UNUSED BOXES ---
        for j in range(len(game), 5):
            self.project_frames[j].config(text=f"Project {j+1}")
            self.project_texts[j].delete("1.0", tk.END)

        # --- SUMMARY ---
        lvl1, lvl2, lvl3, special, habitats = group_animals(game_animals)

        self.summary.delete("1.0", tk.END)

        self.summary.insert(tk.END, "HABITATS:\n")
        self.summary.insert(tk.END, ", ".join(habitats) + "\n\n")

        self.summary.insert(tk.END, f"L1 ({len(lvl1)}):\n{', '.join(lvl1)}\n\n")
        self.summary.insert(tk.END, f"L2 ({len(lvl2)}):\n{', '.join(lvl2)}\n\n")
        self.summary.insert(tk.END, f"L3 ({len(lvl3)}):\n{', '.join(lvl3)}\n\n")

        self.summary.insert(tk.END, f"SPECIAL ({len(special)}):\n{', '.join(special)}\n")


# --- RUN ---
root = tk.Tk()
app = ZooApp(root)
root.mainloop()