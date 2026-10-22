// Dump every text line of a PDF with its position (page, x, y, width, text) as TSV.
// Used for the NHB UP cold storage list: swift tools/data/nhb_pdf_lines.swift UP.pdf lines.tsv
import Foundation
import PDFKit
let args = CommandLine.arguments
guard args.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else { print("cannot open"); exit(1) }
var rows: [String] = ["page\tx\ty\tw\ttext"]
for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i), let sel = page.selection(for: page.bounds(for: .mediaBox)) else { continue }
    for line in sel.selectionsByLine() {
        let b = line.bounds(for: page)
        let t = (line.string ?? "").replacingOccurrences(of: "\t", with: " ").replacingOccurrences(of: "\n", with: " ").trimmingCharacters(in: .whitespaces)
        if t.isEmpty { continue }
        rows.append("\(i + 1)\t\(Int(b.minX))\t\(Int(b.midY))\t\(Int(b.width))\t\(t)")
    }
}
try! rows.joined(separator: "\n").write(toFile: args[2], atomically: true, encoding: .utf8)
print("lines:", rows.count - 1)
