const fs = require("fs");
const { d, FONT } = require("./lib");
const parts = ["s0_title", "s1_intro", "s2_related", "s3_method", "s4_results", "s5_discussion", "s6_threats", "s7_end", "s8_refs"]
  .flatMap((f) => require("./" + f));
const H = (size) => ({ run: { font: FONT, size, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true } });
const doc = new d.Document({
  creator: "Saurabh Choudhary", title: "COCOMO-Extended manuscript",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } }, heading1: H(28), heading2: H(24), heading3: H(22) },
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: d.LevelFormat.BULLET, text: "•", alignment: d.AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } }, run: { font: FONT } } }] },
    { reference: "num1", levels: [{ level: 0, format: d.LevelFormat.DECIMAL, text: "%1.", alignment: d.AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new d.Footer({ children: [new d.Paragraph({ alignment: d.AlignmentType.CENTER,
      children: [new d.TextRun({ children: [d.PageNumber.CURRENT], font: FONT, size: 22 })] })] }) },
    children: parts,
  }],
});
d.Packer.toBuffer(doc).then((b) => { fs.writeFileSync("COCOMO_Extended_manuscript.docx", b); console.log("written", b.length); });
