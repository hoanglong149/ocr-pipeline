#!/usr/bin/env swift
// ocr-vision.swift — macOS Vision OCR, local, no API
// Usage: swift ocr-vision.swift <image> [lang]
// lang: zh-Hans (default), vi-VN, en-US, zh-Hant
// Output: recognized text to stdout

import Foundation
import Vision
import AppKit

func errPrint(_ msg: String) {
    FileHandle.standardError.write((msg + "\n").data(using: .utf8)!)
}

guard CommandLine.arguments.count >= 2 else {
    errPrint("Usage: ocr-vision <image-path> [lang]")
    exit(1)
}

let path = CommandLine.arguments[1]
let lang = CommandLine.arguments.count >= 3 ? CommandLine.arguments[2] : "zh-Hans"

guard let img = NSImage(contentsOfFile: path),
      let cgImage = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    errPrint("ERROR: cannot load image: \(path)")
    exit(1)
}

let request = VNRecognizeTextRequest { req, err in
    guard err == nil, let results = req.results as? [VNRecognizedTextObservation] else {
        errPrint("ERROR: \(err?.localizedDescription ?? "unknown")")
        exit(1)
    }
    for obs in results {
        if let candidate = obs.topCandidates(1).first {
            print(candidate.string)
        }
    }
}
request.recognitionLevel = VNRequestTextRecognitionLevel.accurate
request.recognitionLanguages = [lang]
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try? handler.perform([request])
