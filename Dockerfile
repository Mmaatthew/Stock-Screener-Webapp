FROM python:3.10-slim

# Install Chrome and ChromeDriver
RUN apt-get update && apt-get install -y chromium-chromedriver

# Set up the application directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the app
COPY . .

# Expose the port
EXPOSE 3000

# Run the application
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:3000", "Screener_Webapp:app"]
