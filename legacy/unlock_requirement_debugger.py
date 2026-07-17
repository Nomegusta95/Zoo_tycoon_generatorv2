def analyze_high_tier_animals(pool):

    print("\n=== LVL3 & SPECIAL ANALYSIS ===\n")

    # --- helper ---
    def matches_unlock_group(animal, req_group):
        if not req_group:
            return True

        req_groups = req_group.split(";")
        animal_groups = animal.get("groups", [])

        return any(g in animal_groups for g in req_groups)

    def count_group(pool, req_group, exclude_name):
        return sum(
            1 for a in pool
            if a["name"] != exclude_name
            and matches_unlock_group(a, req_group)
        )

    for a in pool:

        if a["level"] != 3 and not a.get("special"):
            continue

        name = a["name"]
        lvl = a["level"]
        special = a.get("special", False)
        groups = a.get("groups", [])

        req_group = a.get("unlock_group")
        req_count = a.get("unlock_count", 0)

        print(f"{name}")
        print(f"  Level: {lvl} | Special: {special}")
        print(f"  Groups: {groups}")

        if req_group:
            current = count_group(pool, req_group, name)
            status = "OK" if current >= req_count else "MISSING"

            print(f"  Requirement: {req_count} x ({req_group.replace(';', ' OR ')})")
            print(f"  In pool (excluding itself): {current} → {status}")

            # 🔍 EXTRA DEBUG
            matching = [
                x["name"] for x in pool
                if x["name"] != name
                and matches_unlock_group(x, req_group)
            ]

            print(f"  Matching animals: {matching}")

        else:
            print("  Requirement: None")

        print("-" * 40)