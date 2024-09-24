# Use a slim Python image as the base
FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y wget curl unzip \
    && apt-get install -y libnss3 libgconf-2-4 libxi6 libxrender1 libxrandr2 xdg-utils fonts-liberation

# Install Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

# Install ChromeDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` \
    && wget -N https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Set up the application directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the container
COPY . .

# Expose port 3000 for the web app
EXPOSE 3000

# Set the default command to run the application
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:3000", "Screener_Webapp:app"]
