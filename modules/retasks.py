"""
modules/retasks.py — Recovery of incomplete batch uploads on bot restart
"""
import asyncio
from logger import LOGGER
from master.database import db_instance
from constant import msg


async def recover_incomplete_batches(bot):
    """On bot startup, find and resume any incomplete batch uploads."""
    try:
        incomplete = await db_instance.get_incomplete_batches()

        if not incomplete:
            LOGGER.info("No incomplete batches to recover")
            return

        LOGGER.info(f"Found {len(incomplete)} incomplete batches to recover")

        for task in incomplete:
            try:
                user_id = task.get("user_id")
                course_id = task.get("course_id")

                batch = await db_instance.get_batch_by_course_id(course_id)
                if not batch:
                    LOGGER.warning(f"Batch info not found for course_id: {course_id}")
                    continue

                token = batch.get("token", "")
                group_id = batch.get("group_id", "")
                course_name = batch.get("select", "Unknown")

                LOGGER.info(f"Recovering batch: {course_name} ({course_id})")

                try:
                    await bot.send_message(
                        int(group_id),
                        msg.RECOVERING_BATCH.format(course_name)
                    )
                except:
                    pass

                from modules.cpdata import collect_data
                from modules.tasks import process_batch_upload

                all_data = await collect_data(course_id, token)

                if all_data:
                    LOGGER.info(f"Resuming batch {course_id}: {len(all_data)} items")
                    asyncio.create_task(process_batch_upload(bot, course_id, all_data))
                else:
                    LOGGER.warning(f"No data found for batch {course_id}")

                await asyncio.sleep(5)

            except Exception as e:
                LOGGER.error(f"Error recovering batch: {e}")
                continue

    except Exception as e:
        LOGGER.error(f"Error in recover_incomplete_batches: {e}")
