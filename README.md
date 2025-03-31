# Inbox Genie

An AI-powered Cold Email Personalization Assistant that tailors outreach emails to maximize response rates.

## Overview

Inbox Genie is a web application that helps users craft highly effective cold emails by analyzing recipient data and generating personalized messages. The application leverages OpenAI's GPT models to create emails that are professional, conversational, and tailored to the specific recipient.

## Features

- **Analyze Recipient Data**: Process information like name, role, company, LinkedIn profile, recent activities, industry news, and pain points
- **Personalize the Opening**: Craft compelling first sentences based on the recipient's background or recent work
- **Highlight Relevance**: Show how your product/service solves specific challenges they may face
- **Keep it Concise & Value-Driven**: Avoid fluff and generic compliments; focus on clear benefits
- **End with a Strong CTA**: Suggest a non-pushy, actionable next step

## Installation

1. Clone this repository to your local machine
2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with the following contents:

```
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_flask_secret_key_here
```

## Running the Application

To start the application locally:

```
cd src
python app.py
```

The application will be available at http://localhost:5000

## Project Structure

```
inbox-genie/
├── requirements.txt      # Python dependencies
├── README.md            # Project documentation
├── .env                 # Environment variables (create this file)
└── src/                 # Source code directory
    ├── app.py           # Main Flask application
    ├── templates/       # HTML templates
    │   ├── index.html   # Main page template
    │   └── about.html   # About page template
    └── static/          # Static assets
        ├── css/         # CSS stylesheets
        │   └── styles.css
        └── js/          # JavaScript files
            └── script.js
```

## How to Use

1. Fill in the recipient information form with as much detail as possible
2. Click "Generate Personalized Email"
3. Wait for the AI to generate a personalized cold email
4. Copy the generated email using the copy button
5. Customize further if needed and send to your recipient

## Requirements

- Python 3.7+
- Flask
- OpenAI API key
- Internet connection for loading external CSS/JS libraries

## Note

This application requires an OpenAI API key to function. Make sure to set this up in your `.env` file before running the application.
