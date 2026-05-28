import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger("CP_AUTO_UPLOADER")
LOGGER.info("Classplus Auto Uploader Bot Starting...")
