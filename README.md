# TavLite

TavLite is a lightweight, open-source local AI chat application for creating immersive role-playing experiences. Build and manage character cards, chat with any OpenAI-compatible LLM, and generate images — all running locally on your own machine with no cloud dependency.

![s_1](./public/img/screenshots/s_1.webp "s_1")

## Features

- **OpenAI-Compatible API** — Works with any LLM provider that supports the OpenAI API format
- **Streaming Chat** — Real-time SSE streaming with Markdown rendering and thinking process display
- **Multiple Conversation Modes** — Choose from GM (Game Master), NPC, or Novel mode for different storytelling styles
- **Character Card Management** — Create, edit, import, and export character cards; supports SillyTavern PNG card import
- **Text-to-Image Generation** — Integrates with ComfyUI for AI image generation (ZIT, SDXL, and Anima models)
- **Mobile-Friendly** — Responsive design for both desktop and mobile; access via `tavlite.local` through mDNS
- **Light & Dark Themes** — Switch between light and dark mode with persistent preference
- **Conversation History** — Auto-save chat history per character card
- **System Tray** — Runs quietly in the background with quick-access menu
- **QR Code Sharing** — Scan a QR code from your phone to instantly access the chat interface on mobile

## Logo

<img src="./public/img/logo.png" alt="logo" width="150">

## Screenshots

### Configurable Settings

![s_2](./public/img/screenshots/s_2.webp "s_2")

### Character Card Management & Editing

![s_3](./public/img/screenshots/s_3.webp "s_3")

### Streaming Chat with Markdown & Theme Switching

![s_5](./public/img/screenshots/s_5.webp "s_5")

## Installation

### Method 1: Install using the package

Download the latest installer from the [Releases page](https://github.com/Karasukaigan/TavLite/releases) and install it locally.

### Method 2: Deploy from source

```bash
git clone https://github.com/Karasukaigan/TavLite.git
cd TavLite

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

python server.py
```

> Note: Please deploy TavLite within a trusted local area network. Do not deploy TavLite on public cloud servers.

## TavLite Pro

[TavLite Pro](https://beyondblackwall.com/product/2) builds on everything above with additional features designed for serious character card creators and immersive RP enthusiasts:

* **Custom Tags** — Organize and filter character cards with custom tags for quick searching.
   ![s_6](./public/img/screenshots/s_6.webp "s_6")
* **Image Library** — Upload multiple images with descriptions. The AI inserts them into conversations at the right moments — perfect for event CGs and visual storytelling.
   ![s_7](./public/img/screenshots/s_7.webp "s_7")
* **Module Presets & Custom Modules** — Add structured features like time tracking, character stats, and status displays to your cards with one click.
   ![s_8](./public/img/screenshots/s_8.webp "s_8")
* **Card Authoring Assistant** — AI-powered tools for description polishing, opening message generation, text-to-image prompt creation, tag generation, and translation.
   ![s_9](./public/img/screenshots/s_9.webp "s_9")
* **Welcome Page** — Attach custom HTML pages to character cards for introductions, game rules, persona setup, and interactive openings — with AI-assisted generation.
   ![s_10](./public/img/screenshots/s_10.webp "s_10")
* **Usage Statistics** — Track your token consumption per model with visual charts, updated in real time.
   ![s_11](./public/img/screenshots/s_11.webp "s_11")
* **Privacy & Security** — Password protection and HTTPS encryption to keep your conversations private.
   ![s_12](./public/img/screenshots/s_12.webp "s_12")

Your purchase directly supports the ongoing development of TavLite. Thank you!

## Contributing

[Issues](https://github.com/Karasukaigan/TavLite/issues) and [Pull Requests](https://github.com/Karasukaigan/TavLite/pulls) are welcome to help improve this project.

## License

This project is licensed under the [MIT License](./LICENSE).
