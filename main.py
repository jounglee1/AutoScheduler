from dotenv import load_dotenv
from scheduler.agent import AutoSchedulerAgent

load_dotenv()


def main():
    agent = AutoSchedulerAgent()

    conversation = """
    Hey, can we schedule a team meeting next Monday at 2pm for about an hour?
    Also, don't forget the client call on Wednesday morning at 10.
    """

    slots = agent.run(conversation_input=conversation)

    print("Suggested time slots:")
    for slot in slots:
        print(f"  {slot.start} ~ {slot.end}  (score: {slot.score:.2f})  {slot.reason or ''}")


if __name__ == "__main__":
    main()
