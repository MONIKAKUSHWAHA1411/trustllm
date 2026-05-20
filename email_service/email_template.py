"""Premium welcome-email template for TrustLLM.

Bold gradient / brand-heavy visual direction with a live-feeling stat
highlights row. Pure inline-CSS table-based markup so it renders in
Gmail, Apple Mail, Outlook web, and mobile mail clients.

Public API:
    get_welcome_html(display_name) -> str
    get_welcome_text(display_name) -> str
"""

# Stat strings shown in the stats row. Kept in sync with the app's hero
# stats fallback so the email feels consistent with the landing page.
_STAT_PROMPTS = "163"
_STAT_MODELS = "6"
_STAT_TRUST = "0.76"

# Primary CTA destinations
_PRIMARY_CTA_URL = "https://ai-evals-trustllm-upgrade.streamlit.app"
_LEADERBOARD_URL = "https://ai-evals-trustllm-upgrade.streamlit.app/#leaderboard"


def get_welcome_html(display_name: str = "") -> str:
    greeting_name = display_name.strip() if display_name else ""
    greeting = f"Hi {greeting_name}," if greeting_name else "Welcome aboard,"

    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta name="color-scheme" content="dark" />
  <meta name="supported-color-schemes" content="dark" />
  <title>Welcome to TrustLLM</title>
  <!--[if mso]>
  <xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml>
  <![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#05050f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#e5e7eb;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">

  <!-- Preheader (hidden, shows as preview text in inbox) -->
  <div style="display:none;font-size:1px;color:#05050f;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">
    You're in. Let's evaluate some LLMs together.
  </div>

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#05050f;min-height:100%;">
    <tr>
      <td align="center" style="padding:32px 12px 48px;">

        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;">

          <!-- ─── Brand bar ─── -->
          <tr>
            <td style="padding:0 4px 24px;" align="left">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="background:linear-gradient(135deg,#8b5cf6 0%,#6366f1 100%);
                             background-color:#6366f1;
                             width:38px;height:38px;border-radius:10px;
                             text-align:center;vertical-align:middle;
                             font-size:1.2rem;line-height:38px;
                             box-shadow:0 8px 24px rgba(99,102,241,0.4);">
                    🛡
                  </td>
                  <td style="padding-left:12px;font-size:1.15rem;font-weight:700;
                             color:#ffffff;letter-spacing:-0.01em;vertical-align:middle;">
                    TrustLLM
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ─── HERO with bold gradient ─── -->
          <tr>
            <td style="background-color:#4c1d95;
                       background-image:linear-gradient(135deg,#7c3aed 0%,#6366f1 45%,#3b82f6 100%);
                       border-radius:24px;padding:56px 40px 48px;text-align:center;
                       box-shadow:0 24px 60px rgba(99,102,241,0.35);">

              <!-- Rocket emblem -->
              <div style="font-size:3rem;line-height:1;margin-bottom:18px;
                          text-shadow:0 6px 24px rgba(0,0,0,0.35);">
                🚀
              </div>

              <!-- Headline -->
              <h1 style="margin:0 0 14px;font-size:2.4rem;line-height:1.15;
                         font-weight:800;color:#ffffff;letter-spacing:-0.025em;">
                Welcome to TrustLLM
              </h1>

              <!-- Subheadline -->
              <p style="margin:0 0 32px;font-size:1.05rem;line-height:1.55;
                        color:rgba(255,255,255,0.92);max-width:440px;
                        margin-left:auto;margin-right:auto;font-weight:400;">
                The AI evaluation platform built for builders who care about
                reliability, safety, and accuracy.
              </p>

              <!-- Primary CTA -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" style="margin:0 auto;">
                <tr>
                  <td style="border-radius:12px;background:#ffffff;
                             box-shadow:0 12px 28px rgba(0,0,0,0.25);">
                    <a href="{_PRIMARY_CTA_URL}"
                       style="display:inline-block;padding:16px 38px;
                              font-size:1rem;font-weight:700;
                              color:#4c1d95;text-decoration:none;letter-spacing:-0.01em;">
                      Start Exploring →
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ─── Spacer ─── -->
          <tr><td style="height:32px;line-height:32px;font-size:0;">&nbsp;</td></tr>

          <!-- ─── Greeting card ─── -->
          <tr>
            <td style="background-color:#13132a;
                       background-image:linear-gradient(160deg,#1a1640 0%,#0f0f23 100%);
                       border:1px solid rgba(139,92,246,0.15);
                       border-radius:20px;padding:36px 36px 28px;">
              <p style="margin:0 0 12px;font-size:0.95rem;color:#a5b4fc;
                        font-weight:600;letter-spacing:0.04em;text-transform:uppercase;">
                {greeting}
              </p>
              <p style="margin:0;font-size:1.05rem;line-height:1.65;color:#e5e7eb;">
                You just joined a growing community of AI builders evaluating their
                models on real-world prompts. Here's what the platform looks like
                in numbers right now:
              </p>
            </td>
          </tr>

          <!-- ─── Spacer ─── -->
          <tr><td style="height:16px;line-height:16px;font-size:0;">&nbsp;</td></tr>

          <!-- ─── STAT HIGHLIGHTS row ─── -->
          <tr>
            <td>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <!-- Stat 1 -->
                  <td width="33%" valign="top" style="padding:0 6px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="background-color:#5b21b6;
                                   background-image:linear-gradient(160deg,#7c3aed 0%,#5b21b6 100%);
                                   border-radius:16px;padding:24px 16px;text-align:center;
                                   box-shadow:0 10px 24px rgba(124,58,237,0.25);">
                          <div style="font-size:2.1rem;font-weight:800;color:#ffffff;
                                      line-height:1;letter-spacing:-0.02em;">
                            {_STAT_PROMPTS}
                          </div>
                          <div style="margin-top:8px;font-size:0.78rem;color:rgba(255,255,255,0.85);
                                      font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">
                            Prompts<br/>evaluated
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <!-- Stat 2 -->
                  <td width="33%" valign="top" style="padding:0 6px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="background-color:#4338ca;
                                   background-image:linear-gradient(160deg,#6366f1 0%,#4338ca 100%);
                                   border-radius:16px;padding:24px 16px;text-align:center;
                                   box-shadow:0 10px 24px rgba(99,102,241,0.25);">
                          <div style="font-size:2.1rem;font-weight:800;color:#ffffff;
                                      line-height:1;letter-spacing:-0.02em;">
                            {_STAT_MODELS}
                          </div>
                          <div style="margin-top:8px;font-size:0.78rem;color:rgba(255,255,255,0.85);
                                      font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">
                            Models<br/>tested
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <!-- Stat 3 -->
                  <td width="33%" valign="top" style="padding:0 6px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="background-color:#1d4ed8;
                                   background-image:linear-gradient(160deg,#3b82f6 0%,#1d4ed8 100%);
                                   border-radius:16px;padding:24px 16px;text-align:center;
                                   box-shadow:0 10px 24px rgba(59,130,246,0.25);">
                          <div style="font-size:2.1rem;font-weight:800;color:#ffffff;
                                      line-height:1;letter-spacing:-0.02em;">
                            {_STAT_TRUST}
                          </div>
                          <div style="margin-top:8px;font-size:0.78rem;color:rgba(255,255,255,0.85);
                                      font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">
                            Avg trust<br/>score
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ─── Spacer ─── -->
          <tr><td style="height:32px;line-height:32px;font-size:0;">&nbsp;</td></tr>

          <!-- ─── What's included card ─── -->
          <tr>
            <td style="background-color:#13132a;
                       background-image:linear-gradient(160deg,#1a1640 0%,#0f0f23 100%);
                       border:1px solid rgba(139,92,246,0.15);
                       border-radius:20px;padding:36px;">

              <h2 style="margin:0 0 24px;font-size:1.35rem;font-weight:700;color:#ffffff;
                         letter-spacing:-0.015em;">
                Everything you get out of the box
              </h2>

              <!-- Feature 1 -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
                <tr>
                  <td width="44" valign="top" style="padding-right:14px;">
                    <div style="width:44px;height:44px;border-radius:12px;
                                background:linear-gradient(135deg,#a78bfa,#7c3aed);
                                text-align:center;line-height:44px;font-size:1.2rem;">
                      🔍
                    </div>
                  </td>
                  <td valign="top">
                    <div style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:4px;">
                      Hallucination Detection
                    </div>
                    <div style="font-size:0.92rem;line-height:1.55;color:#9ca3af;">
                      Surface factual inconsistencies and grounding failures
                      across your model outputs.
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Feature 2 -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
                <tr>
                  <td width="44" valign="top" style="padding-right:14px;">
                    <div style="width:44px;height:44px;border-radius:12px;
                                background:linear-gradient(135deg,#818cf8,#4f46e5);
                                text-align:center;line-height:44px;font-size:1.2rem;">
                      📊
                    </div>
                  </td>
                  <td valign="top">
                    <div style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:4px;">
                      Prompt-Level Evaluation
                    </div>
                    <div style="font-size:0.92rem;line-height:1.55;color:#9ca3af;">
                      Run systematic evals across your prompt dataset — correctness,
                      relevance, clarity, safety.
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Feature 3 -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:18px;">
                <tr>
                  <td width="44" valign="top" style="padding-right:14px;">
                    <div style="width:44px;height:44px;border-radius:12px;
                                background:linear-gradient(135deg,#60a5fa,#2563eb);
                                text-align:center;line-height:44px;font-size:1.2rem;">
                      🧪
                    </div>
                  </td>
                  <td valign="top">
                    <div style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:4px;">
                      RAG &amp; Agentic AI Testing
                    </div>
                    <div style="font-size:0.92rem;line-height:1.55;color:#9ca3af;">
                      Evaluate retrieval-augmented pipelines and autonomous
                      agents end-to-end.
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Feature 4 -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td width="44" valign="top" style="padding-right:14px;">
                    <div style="width:44px;height:44px;border-radius:12px;
                                background:linear-gradient(135deg,#22d3ee,#0891b2);
                                text-align:center;line-height:44px;font-size:1.2rem;">
                      📈
                    </div>
                  </td>
                  <td valign="top">
                    <div style="font-size:1rem;font-weight:700;color:#ffffff;margin-bottom:4px;">
                      Model Leaderboards
                    </div>
                    <div style="font-size:0.92rem;line-height:1.55;color:#9ca3af;">
                      Benchmark models side-by-side. Spot failure patterns
                      and regressions early.
                    </div>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- ─── Spacer ─── -->
          <tr><td style="height:28px;line-height:28px;font-size:0;">&nbsp;</td></tr>

          <!-- ─── Dual CTAs ─── -->
          <tr>
            <td align="center">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="padding-right:8px;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="background-color:#6366f1;
                                   background-image:linear-gradient(135deg,#7c3aed,#6366f1);
                                   border-radius:12px;
                                   box-shadow:0 12px 28px rgba(99,102,241,0.4);">
                          <a href="{_PRIMARY_CTA_URL}"
                             style="display:inline-block;padding:14px 28px;
                                    font-size:0.95rem;font-weight:700;
                                    color:#ffffff;text-decoration:none;letter-spacing:-0.01em;">
                            Run your first eval →
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td style="padding-left:8px;">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td style="background-color:transparent;
                                   border:1.5px solid rgba(139,92,246,0.5);
                                   border-radius:12px;">
                          <a href="{_LEADERBOARD_URL}"
                             style="display:inline-block;padding:12.5px 26px;
                                    font-size:0.95rem;font-weight:700;
                                    color:#a78bfa;text-decoration:none;letter-spacing:-0.01em;">
                            View Leaderboard
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ─── Spacer ─── -->
          <tr><td style="height:36px;line-height:36px;font-size:0;">&nbsp;</td></tr>

          <!-- ─── Founder signature ─── -->
          <tr>
            <td style="padding:0 12px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td width="48" valign="middle" style="padding-right:14px;">
                    <div style="width:48px;height:48px;border-radius:50%;
                                background:linear-gradient(135deg,#8b5cf6,#6366f1);
                                text-align:center;line-height:48px;font-size:1.1rem;
                                color:#ffffff;font-weight:700;">
                      M
                    </div>
                  </td>
                  <td valign="middle">
                    <div style="font-size:0.95rem;font-weight:700;color:#ffffff;line-height:1.3;">
                      Monika Kushwaha
                    </div>
                    <div style="font-size:0.85rem;color:#9ca3af;margin-top:2px;">
                      Founder, TrustLLM ·
                      <a href="https://www.linkedin.com/in/monika-kushwaha-141/"
                         style="color:#a78bfa;text-decoration:none;">LinkedIn ↗</a>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ─── Spacer ─── -->
          <tr><td style="height:32px;line-height:32px;font-size:0;">&nbsp;</td></tr>

          <!-- ─── Footer ─── -->
          <tr>
            <td align="center" style="padding:24px 12px 0;border-top:1px solid rgba(139,92,246,0.15);">
              <div style="font-size:0.78rem;color:#6b7280;letter-spacing:0.04em;
                          font-weight:600;text-transform:uppercase;margin-bottom:8px;">
                TrustLLM · AI Model Evaluation Platform
              </div>
              <div style="font-size:0.78rem;color:#4b5563;">
                © 2026 TrustLLM · <a href="https://trustllm.site"
                   style="color:#6b7280;text-decoration:none;">trustllm.site</a>
              </div>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def get_welcome_text(display_name: str = "") -> str:
    """Plain-text fallback for clients that don't render HTML."""
    greeting_name = display_name.strip() if display_name else ""
    greeting = f"Hi {greeting_name}," if greeting_name else "Welcome aboard,"

    return f"""{greeting}

Welcome to TrustLLM — the AI evaluation platform built for builders
who care about reliability, safety, and accuracy.

By the numbers right now:
  • {_STAT_PROMPTS} prompts evaluated
  • {_STAT_MODELS}   models tested
  • {_STAT_TRUST} avg trust score

What you get out of the box:

  🔍 Hallucination Detection
     Surface factual inconsistencies and grounding failures across
     your model outputs.

  📊 Prompt-Level Evaluation
     Run systematic evals across your prompt dataset — correctness,
     relevance, clarity, safety.

  🧪 RAG & Agentic AI Testing
     Evaluate retrieval-augmented pipelines and autonomous agents
     end-to-end.

  📈 Model Leaderboards
     Benchmark models side-by-side. Spot failure patterns and
     regressions early.

→ Run your first eval:   {_PRIMARY_CTA_URL}
→ View the leaderboard:  {_LEADERBOARD_URL}

---
Monika Kushwaha
Founder, TrustLLM
LinkedIn: https://www.linkedin.com/in/monika-kushwaha-141/

© 2026 TrustLLM · trustllm.site
"""
