# Use official Python image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set environment variables (will be overridden in production by Render environment)
# ENV API_ID="your_api_id"
# ENV API_HASH="your_api_hash"
# ENV TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
# ENV PHONE_NUMBER="your_phone_number"

# Expose the port for the bot (optional for development)
# EXPOSE 8443

# Command to run the bot
CMD ["python", "bot.py"]
