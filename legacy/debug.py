from data_loader import load_animals   # adjust filename
from project_generator import generate_project

if __name__ == "__main__":

    print("LOADING ANIMALS...")

    animals = load_animals("Animals.xlsx")  # 🔴 your file path

    print(f"Loaded {len(animals)} animals")

    usage = {}

    print("\nGENERATING PROJECTS:\n")

    for i in range(10):

        project = generate_project(animals, usage)

        if not project:
            print(f"{i+1}: FAILED")
            continue

        print(f"{i+1:02d} | diff={project['difficulty']:>3} | {project['animals']}")