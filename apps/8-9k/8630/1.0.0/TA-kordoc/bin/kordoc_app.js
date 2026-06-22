import { parse } from "kordoc";
import { readFileSync, existsSync } from "fs";
// [핵심] 스플렁크가 엉뚱한 임시폴더에서 폰트 매핑(CMap) 파일을 찾지 못하도록, 현재 실행 위치를 앱 폴더로 강력 고정합니다.
if (typeof __dirname !== 'undefined') {
    process.chdir(__dirname);
}
// [OS 공통 방어 로직] PDF.js 엔진이 요구하는 가짜 브라우저 환경 완벽 구현
const _global = globalThis;
if (!_global.DOMMatrix) {
    _global.DOMMatrix = class DOMMatrix {
        a = 1;
        b = 0;
        c = 0;
        d = 1;
        e = 0;
        f = 0;
        // 배열 형태로 넘어오는 매트릭스 변환값을 정확히 받아주어야 글자가 투명해지지 않습니다.
        constructor(init) {
            if (init && init.length >= 6) {
                this.a = init[0];
                this.b = init[1];
                this.c = init[2];
                this.d = init[3];
                this.e = init[4];
                this.f = init[5];
            }
        }
    };
}
if (!_global.Path2D)
    _global.Path2D = class Path2D {
    };
if (!_global.ImageData)
    _global.ImageData = class ImageData {
    };
const args = process.argv.slice(2);
let filePath = "";
for (const arg of args) {
    if (arg.startsWith('file=')) {
        filePath = arg.split('=')[1].replace(/^["']|["']$/g, '');
    }
}
async function processDocument() {
    console.log("filename,success,markdown,error_message");
    if (!filePath || !existsSync(filePath)) {
        console.log(`"${filePath}",false,"","File not found"`);
        process.exit(1);
    }
    try {
        const buffer = readFileSync(filePath);
        // 드디어 교체된 최신 1.7.1 엔진이 동작합니다!
        const result = await parse(buffer.buffer);
        if (result.success) {
            const escapedMarkdown = result.markdown.replace(/"/g, '""');
            console.log(`"${filePath}",true,"${escapedMarkdown}",""`);
        }
        else {
            const realError = result.error || result.message || JSON.stringify(result);
            const escapedError = String(realError).replace(/"/g, '""');
            console.log(`"${filePath}",false,"","[상세 에러] ${escapedError}"`);
        }
    }
    catch (error) {
        console.log(`"${filePath}",false,"","[시스템 에러] ${error.message}"`);
    }
    process.exit(0);
}
processDocument();
