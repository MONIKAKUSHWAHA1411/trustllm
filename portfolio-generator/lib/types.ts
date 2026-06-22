export interface PortfolioSkills {
  languages: string[];
  frameworks: string[];
  aiml: string[];
  cloud: string[];
  databases: string[];
  tools: string[];
}

export interface PortfolioExperience {
  company: string;
  role: string;
  startDate: string;
  endDate: string;
  location?: string;
  description: string[];
}

export interface PortfolioEducation {
  institution: string;
  degree: string;
  startDate: string;
  endDate: string;
  grade?: string;
}

export interface PortfolioProject {
  name: string;
  description: string;
  techStack: string[];
  github?: string;
  live?: string;
}

export interface PortfolioCertification {
  name: string;
  issuer: string;
  date: string;
  url?: string;
}

export interface PortfolioData {
  name: string;
  title: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin?: string;
  github?: string;
  website?: string;
  summary: string;
  skills: PortfolioSkills;
  experience: PortfolioExperience[];
  education: PortfolioEducation[];
  projects: PortfolioProject[];
  certifications: PortfolioCertification[];
}
