from dotenv import load_dotenv
from scheduler.agent import AutoSchedulerAgent

load_dotenv()


def main():
    agent = AutoSchedulerAgent()

    conversation = """
    Hey, can we schedule a team meeting next Monday at 2pm for about an hour?
    Also, don't forget the client call on Wednesday morning at 10.
    """

    results = agent.run(conversation_input=conversation)

    for title, (schedule, slots) in results.items():
        print(f"\n[{title}]")
        for i, slot in enumerate(slots):
            print(f"  {i}: {slot.start} ~ {slot.end}  (score: {slot.score:.2f})")

        choice = input("Select slot number (or skip): ").strip()
        if choice.isdigit() and int(choice) < len(slots):
            agent.confirm(schedule, slots[int(choice)])
            print("Uploaded.")
        else:
            print("Skipped.")


if __name__ == "__main__":
    main()
