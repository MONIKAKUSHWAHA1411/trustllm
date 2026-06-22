import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const PARSE_PROMPT = `You are an expert CV/Resume parser. Extract all information from the CV text below and return ONLY a valid JSON object — no markdown fences, no explanation, just the JSON.

Use this exact structure (use null for missing fields, empty arrays [] for missing lists):

{
  "name": "Full Name",
  "title": "Professional Title / Role",
  "email": "email@example.com or null",
  "phone": "phone number or null",
  "location": "City, Country or null",
  "linkedin": "full LinkedIn URL or null",
  "github": "full GitHub URL or null",
  "website": "personal website URL or null",
  "summary": "A compelling 2-3 sentence professional summary written in first person. If not present, craft one from the CV content.",
  "skills": {
    "languages": ["Python", "Java", "TypeScript"],
    "frameworks": ["React", "Spring Boot", "FastAPI"],
    "aiml": ["LangChain", "TensorFlow", "RAG", "LangGraph"],
    "cloud": ["AWS", "Docker", "Kubernetes", "CI/CD"],
    "databases": ["PostgreSQL", "MongoDB", "Redis"],
    "tools": ["Git", "Figma", "Postman", "Jira"]
  },
  "experience": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "startDate": "Jan 2022",
      "endDate": "Present",
      "location": "City, Country or null",
      "description": ["Key achievement or responsibility", "Another bullet point"]
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "degree": "Bachelor of Technology in Computer Science",
      "startDate": "2018",
      "endDate": "2022",
      "grade": "GPA: 3.8/4.0 or null"
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Clear 1-2 sentence description of what it does and its impact.",
      "techStack": ["React", "Node.js", "MongoDB"],
      "github": "full GitHub URL or null",
      "live": "full live demo URL or null"
    }
  ],
  "certifications": [
    {
      "name": "Certification Name",
      "issuer": "Issuing Organization",
      "date": "Month Year or Year",
      "url": "verification URL or null"
    }
  ]
}

CV Text:
`;

async function extractTextFromPdf(buffer: Buffer): Promise<string> {
  const pdfParse = (await import("pdf-parse")).default;
  const data = await pdfParse(buffer);
  return data.text;
}

async function extractTextFromDocx(buffer: Buffer): Promise<string> {
  const mammoth = await import("mammoth");
  const result = await mammoth.extractRawText({ buffer });
  return result.value;
}

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("cv") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No file uploaded." }, { status: 400 });
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    let cvText = "";
    const fileName = file.name.toLowerCase();

    if (fileName.endsWith(".pdf")) {
      cvText = await extractTextFromPdf(buffer);
    } else if (fileName.endsWith(".docx") || fileName.endsWith(".doc")) {
      cvText = await extractTextFromDocx(buffer);
    } else {
      return NextResponse.json(
        { error: "Unsupported file type. Please upload a PDF or DOCX file." },
        { status: 400 }
      );
    }

    if (!cvText.trim()) {
      return NextResponse.json(
        { error: "Could not extract text from the file. Please try a different file." },
        { status: 400 }
      );
    }

    const message = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 4096,
      messages: [
        {
          role: "user",
          content: PARSE_PROMPT + cvText.slice(0, 12000),
        },
      ],
    });

    const rawContent = message.content[0];
    if (rawContent.type !== "text") {
      throw new Error("Unexpected response type from Anthropic");
    }

    const jsonText = rawContent.text.trim();
    const portfolioData = JSON.parse(jsonText);

    return NextResponse.json({ data: portfolioData });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: `Parsing failed: ${message}` }, { status: 500 });
  }
}
