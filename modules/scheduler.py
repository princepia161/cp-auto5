"""
modules/scheduler.py — Daily batch update scheduler (IST timezone)
"""
import asyncio
import pytz
from datetime import datetime, timedelta
from logger import LOGGER
from master.database import db_instance
from constant import msg

IST = pytz.timezone('Asia/Kolkata')


async def get_next_run_time(time_str):
    try:
        now = datetime.now(IST)
        hour, minute = map(int, time_str.split(":"))
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        return next_run
    except Exception as e:
        LOGGER.error(f"Error calculating next run time: {e}")
        return None


async def schedule_batch_update(bot, course_id, time_str, token, length, course_name, group_id):
    """Schedule a batch for daily auto-update at a specified IST time."""
    try:
        while True:
            next_run = await get_next_run_time(time_str)
            if not next_run:
                LOGGER.error(f"Could not calculate next run time for {course_id}")
                break

            now = datetime.now(IST)
            sleep_seconds = (next_run - now).total_seconds()

            LOGGER.info(f"Scheduled: {course_name} ({course_id}) — next run in {sleep_seconds:.0f}s at {next_run.strftime('%H:%M IST')}")
            await asyncio.sleep(sleep_seconds)

            LOGGER.info(f"Starting daily update for {course_name} ({course_id})")

            from modules.cpdata import collect_data
            from modules.tasks import process_batch_upload

            all_data = await collect_data(course_id, token)

            if all_data:
                pdf_count = sum(1 for x in all_data if x.get("type") == "pdf")
                video_count = sum(1 for x in all_data if x.get("type") == "video")

                await process_batch_upload(bot, course_id, all_data)

                try:
                    await bot.send_message(
                        int(group_id),
                        msg.DAILY_UPDATE_COMPLETED.format(course_id, course_name, pdf_count, video_count)
                    )
                except Exception as e:
                    LOGGER.error(f"Could not send completion message: {e}")
            else:
                LOGGER.info(f"No new content for batch {course_id}")
                try:
                    await bot.send_message(
                        int(group_id),
                        msg.NO_NEW_CLASSES.format(course_name)
                    )
                except:
                    pass

    except asyncio.CancelledError:
        LOGGER.info(f"Scheduler cancelled for batch {course_id}")
    except Exception as e:
        LOGGER.error(f"Scheduler error for batch {course_id}: {e}")


async def start_daily_schedulers(bot):
    """Start daily update schedulers for all batches that have a schedule time."""
    try:
        batches = await db_instance.get_all_batches_with_schedule()

        if not batches:
            LOGGER.info("No scheduled batches found")
            return

        LOGGER.info(f"Starting {len(batches)} daily schedulers")

        for batch in batches:
            try:
                course_id = batch.get("course_id", "")
                time_str = batch.get("time", "")
                token = batch.get("token", "")
                length = batch.get("length", 0)
                course_name = batch.get("select", "Unknown")
                group_id = batch.get("group_id", "")

                if time_str and token and group_id:
                    asyncio.create_task(
                        schedule_batch_update(bot, course_id, time_str, token, length, course_name, group_id)
                    )
                    LOGGER.info(f"Scheduler started: {course_name} at {time_str} IST")

            except Exception as e:
                LOGGER.error(f"Error starting scheduler for batch: {e}")

    except Exception as e:
        LOGGER.error(f"Error in start_daily_schedulers: {e}")
