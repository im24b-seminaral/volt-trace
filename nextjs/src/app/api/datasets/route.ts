import { randomUUID } from "crypto";
import { execFile } from "child_process";
import { mkdir, writeFile } from "fs/promises";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { promisify } from "util";

const run = promisify(execFile);
const PYTHON_DIR = path.join(process.cwd(), "..", "python");
const DATA_DIR = path.join(process.cwd(), "data");

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const files = formData.getAll("files") as File[];

  const datasetId = randomUUID();
  const uploadDir = path.join(DATA_DIR, `${datasetId}_raw`);
  const datasetDir = path.join(DATA_DIR, datasetId);
  await mkdir(uploadDir, { recursive: true });

  for (const file of files) {
    const bytes = await file.arrayBuffer();
    await writeFile(path.join(uploadDir, file.name), Buffer.from(bytes));
  }

  const { stdout } = await run("python3", ["-m", "volt_trace.cli", "sort-files", uploadDir, datasetDir], {
    cwd: PYTHON_DIR,
  });
  const result = JSON.parse(stdout);

  return NextResponse.json({ datasetId, ...result });
}