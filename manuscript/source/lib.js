// Formatting helpers: Times New Roman 11 body; H1 14 bold; H2 12 bold; H3 11 bold; APA tables/figures.
const fs = require("fs");
const d = require("docx");
const FONT = "Times New Roman";
const SZ = 22; // 11 pt in half-points

function runs(text, base = {}) {
  // inline markup: **bold**, *italic*, ^sup^, ~sub~
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\^[^^]+\^|~[^~]+~)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new d.TextRun({ text: text.slice(last, m.index), font: FONT, size: SZ, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new d.TextRun({ text: t.slice(2, -2), bold: true, font: FONT, size: SZ, ...base }));
    else if (t.startsWith("*")) out.push(new d.TextRun({ text: t.slice(1, -1), italics: true, font: FONT, size: SZ, ...base }));
    else if (t.startsWith("^")) out.push(new d.TextRun({ text: t.slice(1, -1), superScript: true, font: FONT, size: SZ, ...base }));
    else out.push(new d.TextRun({ text: t.slice(1, -1), subScript: true, font: FONT, size: SZ, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new d.TextRun({ text: text.slice(last), font: FONT, size: SZ, ...base }));
  return out;
}
const SP = { line: 276, before: 0, after: 120 };
const p = (text, opts = {}) => new d.Paragraph({ children: runs(text), spacing: SP, alignment: d.AlignmentType.JUSTIFIED, ...opts });
const pc = (text) => new d.Paragraph({ children: runs(text), spacing: SP, alignment: d.AlignmentType.CENTER });
const h1 = (t) => new d.Paragraph({ heading: d.HeadingLevel.HEADING_1, children: [new d.TextRun({ text: t, bold: true, font: FONT, size: 28 })] });
const h2 = (t) => new d.Paragraph({ heading: d.HeadingLevel.HEADING_2, children: [new d.TextRun({ text: t, bold: true, font: FONT, size: 24 })] });
const h3 = (t) => new d.Paragraph({ heading: d.HeadingLevel.HEADING_3, children: [new d.TextRun({ text: t, bold: true, font: FONT, size: 22 })] });
const bullets = (items) => items.map((t) => new d.Paragraph({ children: runs(t), numbering: { reference: "bul", level: 0 }, spacing: { line: 276, after: 60 }, alignment: d.AlignmentType.LEFT }));
const numbered = (items, ref = "num1") => items.map((t) => new d.Paragraph({ children: runs(t), numbering: { reference: ref, level: 0 }, spacing: { line: 276, after: 60 }, alignment: d.AlignmentType.LEFT }));
const eq = (text, num) => new d.Paragraph({ children: [...runs(text), new d.TextRun({ text: `\t(${num})`, font: FONT, size: SZ })],
  tabStops: [{ type: d.TabStopType.RIGHT, position: 9026 }], spacing: { before: 120, after: 120, line: 276 }, alignment: d.AlignmentType.CENTER, indent: { left: 720 } });

const TW = 9026; // text width in DXA for A4 with 1-inch margins
const border = { style: d.BorderStyle.SINGLE, size: 6, color: "000000" };
const none = { style: d.BorderStyle.NONE, size: 0, color: "FFFFFF" };
function table(num, title, headers, rows, widths, note) {
  const total = widths.reduce((a, b) => a + b, 0);
  const w = widths.map((x) => Math.round((x * TW) / total));
  w[w.length - 1] += TW - w.reduce((a, b) => a + b, 0);
  const cell = (t, i, isHead, isLast) => new d.TableCell({
    width: { size: w[i], type: d.WidthType.DXA },
    margins: { top: 40, bottom: 40, left: 80, right: 80 },
    borders: { top: isHead ? border : none, bottom: isHead || isLast ? border : none, left: none, right: none },
    children: [new d.Paragraph({ children: runs(String(t), isHead ? { bold: true } : {}), spacing: { line: 240, after: 0 },
      alignment: i === 0 ? d.AlignmentType.LEFT : d.AlignmentType.CENTER })],
  });
  const tbl = new d.Table({
    width: { size: TW, type: d.WidthType.DXA }, columnWidths: w,
    borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
    rows: [new d.TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true, false)) }),
      ...rows.map((r, ri) => new d.TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, ri === rows.length - 1)) }))],
  });
  const out = [
    new d.Paragraph({ children: runs(`Table ${num}`, { bold: true }), spacing: { before: 200, after: 60 }, keepNext: true }),
    new d.Paragraph({ children: runs(title, { italics: true }), spacing: { after: 100 }, keepNext: true }),
    tbl,
  ];
  if (note) out.push(new d.Paragraph({ children: runs("*Note.* " + note), spacing: { before: 60, after: 200, line: 240 } }));
  else out.push(new d.Paragraph({ children: [], spacing: { after: 120 } }));
  return out;
}
function figure(num, title, path, widthIn, note) {
  const img = fs.readFileSync(path);
  // read PNG size
  const wpx = img.readUInt32BE(16), hpx = img.readUInt32BE(20);
  const wPt = widthIn * 72, hPt = (wPt * hpx) / wpx;
  const out = [
    new d.Paragraph({ children: runs(`Figure ${num}`, { bold: true }), spacing: { before: 200, after: 60 }, keepNext: true }),
    new d.Paragraph({ children: runs(title, { italics: true }), spacing: { after: 100 }, keepNext: true }),
    new d.Paragraph({ children: [new d.ImageRun({ type: "png", data: img, transformation: { width: wPt * 96 / 72, height: hPt * 96 / 72 },
      altText: { title: `Figure ${num}`, description: title, name: `figure${num}` } })], alignment: d.AlignmentType.CENTER, keepNext: !!note }),
  ];
  if (note) out.push(new d.Paragraph({ children: runs("*Note.* " + note), spacing: { before: 60, after: 200, line: 240 } }));
  return out;
}
const ref = (text) => new d.Paragraph({ children: runs(text), spacing: { line: 276, after: 80 }, indent: { left: 720, hanging: 720 }, alignment: d.AlignmentType.LEFT });
module.exports = { d, FONT, SZ, runs, p, pc, h1, h2, h3, bullets, numbered, eq, table, figure, ref };
