"""Welcome email template for TrustLLM.

Produces both HTML (primary) and plain-text (fallback) variants.
"""


def get_welcome_html(display_name: str = "") -> str:
    greeting = f"Hi {display_name}," if display_name else "Welcome,"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Welcome to TrustLLM</title>
  <!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#0f172a;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation"
         style="background-color:#0f172a;min-height:100%;">
    <tr>
      <td align="center" style="padding:40px 16px;">

        <table width="600" cellpadding="0" cellspacing="0" border="0" role="presentation"
               style="max-width:600px;width:100%;">

          <!-- ── Logo bar ── -->
          <tr>
            <td style="padding-bottom:28px;" align="center">
              <table cellpadding="0" cellspacing="0" border="0" role="presentation">
                <tr>
                  <td style="background:#4f46e5;width:40px;height:40px;border-radius:10px;
                             text-align:center;vertical-align:middle;font-size:1.3rem;
                             line-height:40px;">
                    🛡
                  </td>
                  <td style="padding-left:10px;font-size:1.25rem;font-weight:700;
                             color:#ffffff;letter-spacing:-0.02em;vertical-align:middle;">
                    TrustLLM
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ── Main card ── -->
          <tr>
            <td style="background:linear-gradient(160deg,#1e1b4b 0%,#1e293b 100%);
                       border:1px solid rgba(255,255,255,0.08);
                       border-radius:16px;padding:44px 40px;">

              <!-- Greeting & headline -->
              <p style="color:#94a3b8;font-size:0.95rem;margin:0 0 8px 0;">{greeting}</p>
              <h1 style="color:#ffffff;font-size:1.9rem;font-weight:800;
                         letter-spacing:-0.03em;margin:0 0 16px 0;line-height:1.2;">
                Welcome to TrustLLM 🚀
              </h1>
              <p style="color:#94a3b8;font-size:0.95rem;line-height:1.75;margin:0 0 32px 0;">
                You're now part of a growing community of AI builders who care about
                reliability, safety, and trust. TrustLLM gives you the tools to evaluate,
                benchmark, and improve your AI systems — before they reach production.
              </p>

              <!-- Feature list -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     role="presentation" style="margin-bottom:36px;">
                <tr>
                  <td style="padding-bottom:10px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation"
                           style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                                  border-radius:10px;padding:16px;">
                      <tr>
                        <td style="width:32px;font-size:1.2rem;vertical-align:top;padding-top:2px;">🔍</td>
                        <td style="padding-left:12px;">
                          <div style="color:#e2e8f0;font-size:0.88rem;font-weight:700;margin-bottom:4px;">
                            Hallucination Detection
                          </div>
                          <div style="color:#64748b;font-size:0.8rem;line-height:1.55;">
                            Automatically surface factual inconsistencies and grounding failures in model responses.
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding-bottom:10px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation"
                           style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                                  border-radius:10px;padding:16px;">
                      <tr>
                        <td style="width:32px;font-size:1.2rem;vertical-align:top;padding-top:2px;">📊</td>
                        <td style="padding-left:12px;">
                          <div style="color:#e2e8f0;font-size:0.88rem;font-weight:700;margin-bottom:4px;">
                            AI Evaluation &amp; Prompt Testing
                          </div>
                          <div style="color:#64748b;font-size:0.8rem;line-height:1.55;">
                            Run systematic evals across your prompt dataset. Score outputs for correctness, safety, and quality.
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding-bottom:10px;">
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation"
                           style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                                  border-radius:10px;padding:16px;">
                      <tr>
                        <td style="width:32px;font-size:1.2rem;vertical-align:top;padding-top:2px;">🧪</td>
                        <td style="padding-left:12px;">
                          <div style="color:#e2e8f0;font-size:0.88rem;font-weight:700;margin-bottom:4px;">
                            RAG &amp; Agentic AI Testing
                          </div>
                          <div style="color:#64748b;font-size:0.8rem;line-height:1.55;">
                            Evaluate retrieval-augmented generation pipelines and autonomous AI agents end-to-end.
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td>
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation"
                           style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);
                                  border-radius:10px;padding:16px;">
                      <tr>
                        <td style="width:32px;font-size:1.2rem;vertical-align:top;padding-top:2px;">📈</td>
                        <td style="padding-left:12px;">
                          <div style="color:#e2e8f0;font-size:0.88rem;font-weight:700;margin-bottom:4px;">
                            Dataset Analysis &amp; Model Benchmarking
                          </div>
                          <div style="color:#64748b;font-size:0.8rem;line-height:1.55;">
                            Compare models side-by-side on leaderboards. Spot failure patterns and regressions early.
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- CTA button -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     role="presentation" style="margin-bottom:36px;">
                <tr>
                  <td align="center">
                    <a href="https://trustllm.site"
                       style="display:inline-block;
                              background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 100%);
                              color:#ffffff;text-decoration:none;
                              font-size:0.95rem;font-weight:700;
                              padding:14px 40px;border-radius:8px;
                              letter-spacing:-0.01em;
                              box-shadow:0 4px 20px rgba(79,70,229,0.45);">
                      Start Exploring TrustLLM →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Divider -->
              <hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:0 0 28px 0;" />

              <!-- Founder section -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0" role="presentation">
                <tr>
                  <!-- Avatar -->
                  <td style="width:46px;vertical-align:middle;">
                    <div style="width:46px;height:46px;border-radius:50%;
                                background:linear-gradient(135deg,#4f46e5,#818cf8);
                                text-align:center;line-height:46px;
                                font-size:1rem;font-weight:700;color:#ffffff;">
                      M
                    </div>
                  </td>
                  <!-- Info -->
                  <td style="padding-left:14px;vertical-align:middle;">
                    <div style="color:#e2e8f0;font-size:0.88rem;font-weight:700;">Monika Kushwaha</div>
                    <div style="color:#64748b;font-size:0.78rem;margin-top:2px;">Founder, TrustLLM</div>
                    <a href="https://www.linkedin.com/in/monika-kushwaha-141/"
                       style="color:#818cf8;font-size:0.78rem;text-decoration:none;">
                      LinkedIn ↗
                    </a>
                  </td>
                  <!-- Tagline -->
                  <td style="vertical-align:middle;text-align:right;">
                    <p style="color:#475569;font-size:0.8rem;margin:0;line-height:1.6;">
                      Questions? Just reply<br>to this email.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- ── Footer ── -->
          <tr>
            <td style="padding-top:28px;" align="center">
              <p style="color:#334155;font-size:0.72rem;margin:0;line-height:1.7;">
                © TrustLLM · AI Model Evaluation Platform<br />
                <a href="https://trustllm.site"
                   style="color:#475569;text-decoration:none;">trustllm.site</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def get_welcome_text(display_name: str = "") -> str:
    greeting = f"Hi {display_name}," if display_name else "Welcome,"
    return f"""{greeting}

Welcome to TrustLLM!

You're now part of a growing community of AI builders who care about
reliability, safety, and trust.

What you can do with TrustLLM:

🔍 Hallucination Detection
   Automatically surface factual inconsistencies and grounding failures.

📊 AI Evaluation & Prompt Testing
   Run systematic evals across your prompt dataset.

🧪 RAG & Agentic AI Testing
   Evaluate RAG pipelines and autonomous agents end-to-end.

📈 Dataset Analysis & Model Benchmarking
   Compare models side-by-side on leaderboards.

Start Exploring → https://trustllm.site

---
Monika Kushwaha
Founder, TrustLLM
LinkedIn: https://www.linkedin.com/in/monika-kushwaha-141/

© TrustLLM · trustllm.site
"""
