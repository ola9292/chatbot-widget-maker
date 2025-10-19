# Chatbot Widget Maker

## About

Chatbot Widget Maker is a powerful yet easy-to-use tool that lets businesses create their own AI chatbot for their websites. Built with **Flask**, **Vue.js**, and the **OpenAI API**, it allows users to provide their business name, email, and a detailed summary of their services to instantly generate an embeddable chatbot script. Visitors can then chat directly on the business website, and the chatbot responds intelligently using only the provided business information.

## Motivation

As a web developer, I noticed that many small business owners wanted a simple way to automate responses on their websites without technical setup or expensive chatbot services. Chatbot Widget Maker was built to solve that, offering a quick, affordable, and customizable solution powered by OpenAI. It helps businesses provide instant answers to customer inquiries while staying true to their brand voice.

## Screenshot

![Chatbot Widget Maker Screenshot](https://github.com/ola9292/chatbot-widget-maker/blob/b0995e6753972233c3dce8f1fe1851cecf4901da/Screenshot%202025-10-07%20at%207.39.12%20pm.png)
![Chatbot Widget Maker Screenshot](https://github.com/ola9292/chatbot-widget-maker/blob/0332595cd997376401af3b35b314a037e28da20b/Screenshot%202025-10-07%20at%207.44.30%20pm.png)

## Framework

**Flask**, **Vue.js**, **OpenAI API**, **SQLAlchemy**

## How to Use

1. Enter your **business name**, **email**, and **detailed summary** about what your business does.
2. The app generates an embeddable script tag such as:

   ```html
   <script src="https://yourdomain.com/widget.js" data-id="1"></script>
   ```
3. Copy and paste this script into your website’s HTML.
4. Visitors can start chatting immediately — the chatbot answers based only on your business summary.

