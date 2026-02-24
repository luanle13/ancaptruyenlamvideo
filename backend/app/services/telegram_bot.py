# AnCapTruyenLamVideo - Telegram Bot Service

import asyncio
import logging
import re
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from ..config import get_settings
from ..models.crawler import CrawlerTaskCreate
from .crawler import CrawlerService

logger = logging.getLogger(__name__)
settings = get_settings()


class TelegramBotService:
    """Telegram bot for triggering manga crawler pipeline."""

    def __init__(self):
        self.application: Optional[Application] = None
        self.active_tasks: dict[int, str] = {}  # chat_id -> task_id

    async def start(self):
        """Start the Telegram bot."""
        if not settings.telegram_bot_token:
            logger.warning("Telegram bot token not configured, skipping bot startup")
            return

        if not settings.telegram_enabled:
            logger.info("Telegram bot is disabled")
            return

        try:
            self.application = (
                Application.builder()
                .token(settings.telegram_bot_token)
                .build()
            )

            # Add handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CommandHandler("status", self._handle_status))
            self.application.add_handler(CommandHandler("cancel", self._handle_cancel))
            self.application.add_handler(CommandHandler("list", self._handle_list))
            self.application.add_handler(CommandHandler("clear", self._handle_clear))
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
            )

            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)

            logger.info("Telegram bot started successfully")

        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")

    async def stop(self):
        """Stop the Telegram bot."""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
Chào mừng đến với AnCapTruyenLamVideo Bot!

Gửi cho tôi URL truyện từ truyenqqno.com để bắt đầu tạo video.

Ví dụ:
https://truyenqqno.com/truyen-tranh/ten-truyen-12345

Các lệnh:
/help - Xem hướng dẫn
/list - Xem danh sách truyện đã xử lý
/status - Xem trạng thái task hiện tại
/cancel - Hủy task đang chạy
/clear - Xóa tất cả task trong database
"""
        await update.message.reply_text(welcome_message)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """
Hướng dẫn sử dụng:

1. Gửi URL truyện từ truyenqqno.com
2. Bot sẽ tự động:
   - Tải ảnh từ các chapter
   - Xử lý AI để tạo kịch bản
   - Tạo video với giọng đọc tiếng Việt
3. Khi hoàn thành, bot sẽ thông báo

Lưu ý:
- Mỗi lần chỉ xử lý 1 truyện
- Thời gian xử lý phụ thuộc vào số chapter
- Trong chế độ dev, chỉ xử lý 5 chapter đầu

Các lệnh:
/start - Bắt đầu
/help - Xem hướng dẫn này
/list - Xem danh sách truyện đã xử lý
/status - Xem trạng thái task
/cancel - Hủy task đang chạy
/clear - Xóa tất cả task trong database
"""
        await update.message.reply_text(help_message)

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        chat_id = update.effective_chat.id
        task_id = self.active_tasks.get(chat_id)

        if not task_id:
            await update.message.reply_text("Không có task nào đang chạy.")
            return

        task = await CrawlerService.get_task(task_id)
        if not task:
            del self.active_tasks[chat_id]
            await update.message.reply_text("Task không tồn tại.")
            return

        status_message = f"""
Task ID: {task_id}
Truyện: {task.get('manga_title', 'Đang xử lý...')}
Trạng thái: {task.get('status', 'unknown')}
Tiến độ: {task.get('progress', 0)}%
"""
        await update.message.reply_text(status_message)

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel command."""
        chat_id = update.effective_chat.id
        task_id = self.active_tasks.get(chat_id)

        if not task_id:
            await update.message.reply_text("Không có task nào đang chạy để hủy.")
            return

        success = await CrawlerService.cancel_task(task_id)
        if success:
            del self.active_tasks[chat_id]
            await update.message.reply_text("Đã hủy task thành công.")
        else:
            await update.message.reply_text("Không thể hủy task (có thể đã hoàn thành hoặc lỗi).")

    async def _handle_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command - show all processed manga."""
        tasks = await CrawlerService.get_all_tasks()

        if not tasks:
            await update.message.reply_text("Chưa có truyện nào được xử lý.")
            return

        # Filter only completed tasks with YouTube uploads
        completed_tasks = [
            task for task in tasks
            if task.get("status") == "completed"
        ]

        if not completed_tasks:
            await update.message.reply_text("Chưa có truyện nào hoàn thành.")
            return

        # Build message
        message_parts = ["📚 Danh sách truyện đã xử lý:\n"]

        for i, task in enumerate(completed_tasks, 1):
            manga_title = task.get("manga_title", "Unknown")
            manga_url = task.get("manga_url", "N/A")
            youtube_video_id = task.get("youtube_video_id")

            entry = f"\n{i}. {manga_title}\n"
            entry += f"   📖 URL: {manga_url}\n"

            if youtube_video_id:
                entry += f"   🎬 YouTube: https://youtube.com/watch?v={youtube_video_id}\n"
            else:
                entry += "   🎬 YouTube: Chưa upload\n"

            message_parts.append(entry)

        full_message = "".join(message_parts)

        # Telegram has a 4096 character limit per message
        if len(full_message) > 4000:
            # Split into multiple messages
            chunks = []
            current_chunk = message_parts[0]

            for part in message_parts[1:]:
                if len(current_chunk) + len(part) > 4000:
                    chunks.append(current_chunk)
                    current_chunk = part
                else:
                    current_chunk += part

            if current_chunk:
                chunks.append(current_chunk)

            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(full_message)

    async def _handle_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command - delete all tasks from database."""
        # Check if there's an active task running
        chat_id = update.effective_chat.id
        if chat_id in self.active_tasks:
            await update.message.reply_text(
                "⚠️ Đang có task đang chạy. Vui lòng đợi hoàn thành hoặc /cancel trước khi xóa."
            )
            return

        await update.message.reply_text("🗑️ Đang xóa tất cả task...")

        try:
            deleted_count = await CrawlerService.delete_all_tasks()

            if deleted_count > 0:
                await update.message.reply_text(
                    f"✅ Đã xóa {deleted_count} task từ database.\n"
                    "📺 Video trên YouTube không bị ảnh hưởng."
                )
            else:
                await update.message.reply_text("ℹ️ Không có task nào để xóa.")

        except Exception as e:
            logger.error(f"Error clearing tasks: {e}")
            await update.message.reply_text(f"❌ Lỗi khi xóa task: {str(e)}")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages (URLs)."""
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        # Check if it's a valid truyenqq URL
        if not self._is_valid_manga_url(text):
            await update.message.reply_text(
                "Vui lòng gửi URL hợp lệ từ truyenqqno.com\n"
                "Ví dụ: https://truyenqqno.com/truyen-tranh/ten-truyen-12345"
            )
            return

        # Check if already processing
        if chat_id in self.active_tasks:
            await update.message.reply_text(
                "Đang có task đang chạy. Vui lòng đợi hoàn thành hoặc /cancel để hủy."
            )
            return

        # Start processing
        await update.message.reply_text(f"Đã nhận URL: {text}\nĐang bắt đầu xử lý...")

        try:
            # Create task
            task_create = CrawlerTaskCreate(manga_url=text)
            task = await CrawlerService.create_task(task_create)
            task_id = task["_id"]

            self.active_tasks[chat_id] = task_id

            await update.message.reply_text(
                f"Đã tạo task: {task_id}\n"
                f"Truyện: {task.get('manga_title', 'Đang lấy thông tin...')}\n"
                "Đang xử lý, vui lòng đợi..."
            )

            # Start crawl in background with notification callback
            asyncio.create_task(
                self._process_with_notification(chat_id, task_id, context)
            )

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            await update.message.reply_text(f"Lỗi khi tạo task: {str(e)}")

    async def _process_with_notification(
        self,
        chat_id: int,
        task_id: str,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """Process the crawl and send notifications."""
        try:
            # Start the crawl
            await CrawlerService.start_crawl(task_id)

            # Get final task status
            task = await CrawlerService.get_task(task_id)

            if task:
                status = task.get("status", "unknown")
                manga_title = task.get("manga_title", "Unknown")

                if status == "completed":
                    video_file = task.get("video_file", "")
                    youtube_video_id = task.get("youtube_video_id", "")
                    message = (
                        f"✅ Hoàn thành!\n\n"
                        f"Truyện: {manga_title}\n"
                        f"Task ID: {task_id}\n"
                    )
                    if video_file:
                        message += f"Video: {video_file}\n"
                    if youtube_video_id:
                        message += f"YouTube: https://youtube.com/watch?v={youtube_video_id}\n"
                    message += "\nCảm ơn bạn đã sử dụng!"

                elif status == "failed":
                    error = task.get("error", "Unknown error")
                    message = (
                        f"❌ Lỗi!\n\n"
                        f"Truyện: {manga_title}\n"
                        f"Task ID: {task_id}\n"
                        f"Lỗi: {error}"
                    )

                elif status == "cancelled":
                    message = f"🚫 Task đã bị hủy.\nTruyện: {manga_title}"

                else:
                    message = f"⚠️ Task kết thúc với trạng thái: {status}"

                await context.bot.send_message(chat_id=chat_id, text=message)

        except Exception as e:
            logger.error(f"Error in process_with_notification: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Lỗi hệ thống: {str(e)}"
            )

        finally:
            # Remove from active tasks
            if chat_id in self.active_tasks:
                del self.active_tasks[chat_id]

    def _is_valid_manga_url(self, url: str) -> bool:
        """Check if URL is a valid truyenqq manga URL."""
        patterns = [
            r"https?://truyenqqno\.com/truyen-tranh/.+",
            r"https?://truyenqq\..+/truyen-tranh/.+",
        ]
        return any(re.match(pattern, url) for pattern in patterns)


# Singleton instance
telegram_bot = TelegramBotService()
