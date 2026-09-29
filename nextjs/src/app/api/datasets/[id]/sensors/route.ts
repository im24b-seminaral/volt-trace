import { execFile } from "child_process";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { promisify } from "util";

const run = promisify(execFile);
const PYTHON_DIR = path.join(process.cwd(), "..", "python");
const DATA_DIR = path.join(process.cwd(), "data");
const PYTHON = process.platform === "win32" ? "python" : "python3";

export async function GET(_request: NextRequest, { params }: { params: { id: string } }) {
    const datasetDir = path.join(DATA_DIR, params.id);
    const { stdout } = await run(PYTHON, ["-m", "volt_trace.cli", "sensors", datasetDir], { cwd: PYTHON_DIR });
    return NextResponse.json(JSON.parse(stdout));
}