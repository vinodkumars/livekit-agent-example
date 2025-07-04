from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession, RoomInputOptions, get_job_context
from livekit.plugins import (
    cartesia,
    deepgram,
    noise_cancellation,
    openai,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from loguru import logger

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        job_context = get_job_context()
        vad: silero.VAD = job_context.proc.userdata["vad"]
        llm = openai.LLM(model="gpt-4o-mini")
        super().__init__(
            instructions="You are a helpful voice AI assistant.",
            stt=deepgram.STT(model="nova-3", language="multi"),
            llm=llm,
            tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
            turn_detection=MultilingualModel(),
            vad=vad,
        )


def prewarm(proc: agents.JobProcess) -> None:
    logger.info("Prewarming agent...")
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: agents.JobContext) -> None:
    logger.info("Starting agent...")

    session: AgentSession = AgentSession()

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: agents.ConversationItemAddedEvent) -> None:
        item = event.item
        if hasattr(item, "role") and hasattr(item, "text_content") and hasattr(item, "interrupted"):
            logger.info(
                f"Conversation item added from {item.role}: {item.text_content} interrupted: {item.interrupted}"
            )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    await ctx.connect()
    # await ctx.wait_for_participant(kind=rtc.ParticipantKind.PARTICIPANT_KIND_SIP)
    await session.generate_reply(
        instructions="Greet the user and offer your assistance.", allow_interruptions=False
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            agent_name="inbound-telephony-agent",
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
