# Screenshot provenance

Captured on 16 November 2026 from the unmodified application source at `d5c6cc7`, built with Vite and served by FastAPI at `http://127.0.0.1:8765`. Playwright drove installed Chromium headlessly at 1440 × 1100 CSS pixels, device scale 1; full-page PNG heights vary. No screenshots were generated, composited or retouched.

| File | Actual state |
| --- | --- |
| `login.png` | Empty crew sign-in form |
| `registration.png` | Empty registration form |
| `dashboard.png` | Seeded fictional Amara Chen scenario |
| `historical-chart.png` | Sleep selected; 14 readings and chart tooltip |
| `health-alerts.png` | Deterministic sleep/fatigue demonstration alerts |
| `daily-check-in.png` | Fictional Synthetic Demo Astronaut account; unconfirmed example inputs |
| `gemini-analysis-unavailable.png` | Actual missing-key response after analysis request |
| `chatbot-unavailable.png` | Synthetic question and actual missing-key response |
| `daily-report-unavailable.png` | Actual missing-key response after report request |

The isolated SQLite file was outside the checkout. Registration used `portfolio-demo@example.com`; no credentials are visible. Check-in example confirmation and successful saving were exercised after capture. A configured Gemini key is needed to capture successful live explanations and reports. Do not substitute mocked output and label it as a live model response.
