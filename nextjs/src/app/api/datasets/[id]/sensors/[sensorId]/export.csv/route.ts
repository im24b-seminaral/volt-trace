import { execFile } from "child_process";
import { NextRequest } from "next/server";
import path from "path";
import { promisify } from "util";

const run = promisify(execFile);
const PYTHON_DIR = path.join(process.cwd(), "..", "python");
const DATA_DIR = path.join(process.cwd(), "data");

export async function GET(_request: NextRequest, { params }: { params: { id: string; sensorId: string } }) {
    const datasetDir = path.join(DATA_DIR, params.id);
    const { stdout } = await run("python3", ["-m", "volt_trace.cli", "export", datasetDir, params.sensorId], { cwd: PYTHON_DIR });
    return new Response(stdout, {
        headers: {
            "Content-Type": "text/csv",
            "Content-Disposition": `attachment; filename=${params.sensorId}.csv`,
        },
    });
}