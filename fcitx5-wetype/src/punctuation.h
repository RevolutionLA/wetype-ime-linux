#pragma once

#include <fcitx-utils/utf8.h>
#include <cstdint>
#include <string_view>

namespace wetype {

// Keys the plugin owns in the Chinese input state. Everything here becomes
// fullwidth; the backslash is the 、 key, and it has no ASCII twin in running
// text, so its halfwidth form is the empty view and the caller lets the key
// through untouched. The grave key deliberately stays a backtick: it is what
// markdown and shell quoting need.
inline std::string_view punctuation(char key, bool fullwidth) {
    switch (key) {
        case ',': return fullwidth ? "，" : ",";
        case '.': return fullwidth ? "。" : ".";
        case '?': return fullwidth ? "？" : "?";
        case '!': return fullwidth ? "！" : "!";
        case ':': return fullwidth ? "：" : ":";
        case ';': return fullwidth ? "；" : ";";
        case '\\': return fullwidth ? "、" : "";
        default: return {};
    }
}

// An owned key, whether it converts to anything at all.
inline bool ownsPunctuation(char key) {
    return !punctuation(key, true).empty();
}

inline bool isDigitCodepoint(std::uint32_t c) { return c >= '0' && c <= '9'; }

// The only in-text exception to fullwidth punctuation: a digit right before the
// cursor, so "3.14" and "1,000" stay ASCII. Trailing spaces do not cancel it,
// because "总分 3 " + "." still follows a number.
inline bool endsWithDigit(std::string_view text) {
    while (!text.empty() && (text.back() == ' ' || text.back() == '\t' ||
                             text.back() == '\n' || text.back() == '\r')) {
        text.remove_suffix(1);
    }
    if (text.empty() || !fcitx::utf8::validate(text)) return false;
    // ASCII digits cannot hide inside a multi-byte sequence: continuation bytes
    // are 0x80-0xBF, so a trailing 0x30-0x39 is a real digit.
    return isDigitCodepoint(static_cast<unsigned char>(text.back()));
}

}  // namespace wetype
