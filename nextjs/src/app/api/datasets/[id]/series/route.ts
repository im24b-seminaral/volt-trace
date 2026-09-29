import { execFile } from "child_process";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { promisify } from "util";

const run = promisify(execFile);
const PYTHON_DIR = path.join(process.cwd(), "..", "python");
const DATA_DIR = path.join(process.cwd(), "data");
const PYTHON = process.platform === "win32" ? "python" : "python3";

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
    const datasetDir = path.join(DATA_DIR, params.id);
    const q = request.nextUrl.searchParams;
    const { stdout } = await run(
        PYTHON,
        ["-m", "volt_trace.cli", "series", datasetDir, q.get("sensorId") ?? "", q.get("kind") ?? "", q.get("resolution") ?? "", q.get("from") ?? "", q.get("to") ?? ""],
        { cwd: PYTHON_DIR }
    );
    return NextResponse.json(JSON.parse(stdout));
}