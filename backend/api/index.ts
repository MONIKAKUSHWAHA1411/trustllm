// Vercel serverless entrypoint — every /api/* request is rewritten here
// (see vercel.json) and handled by the Express app.
import app from "../src/app";

export default app;
