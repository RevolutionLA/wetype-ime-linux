#include "punctuation.h"

#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {

void expectTable() {
    const struct { char key; std::string_view full; std::string_view half; } cases[] = {
        {',', "，", ","},   {'.', "。", "."},   {'?', "？", "?"}, {'!', "！", "!"},
        {':', "：", ":"},   {';', "；", ";"},
    };
    for (const auto &c : cases) {
        if (wetype::punctuation(c.key, true) != c.full)
            throw std::runtime_error(std::string("wrong fullwidth for ") + c.key);
        if (wetype::punctuation(c.key, false) != c.half)
            throw std::runtime_error(std::string("wrong halfwidth for ") + c.key);
        if (!wetype::ownsPunctuation(c.key))
            throw std::runtime_error(std::string("key not owned: ") + c.key);
    }
    // The grave key is the 、 key. It has no halfwidth form: the caller must let
    // the key through rather than commit an empty string.
    if (wetype::punctuation('`', true) != "、" || !wetype::punctuation('`', false).empty())
        throw std::runtime_error("wrong grave/、 handling");
}

void expectOwnedSetIsClosed() {
    const char plain[] = {"aA09 /<>()\"'~@#$%^&*_+-={}[]\\|;:,.?!`"};
    for (const char c : plain) {
        const bool expected = (c == ',' || c == '.' || c == '?' || c == '!' ||
                               c == ':' || c == ';' || c == '`');
        if (wetype::ownsPunctuation(c) != expected)
            throw std::runtime_error("ownership changed for an unlisted key");
    }
    // Shifted forms arrive as their own keysyms and are deliberately unowned.
    if (wetype::ownsPunctuation('<') || wetype::ownsPunctuation('~') ||
        wetype::ownsPunctuation('"'))
        throw std::runtime_error("shifted symbol should stay untouched");
}

void expectDigitException() {
    const std::pair<std::string_view, bool> cases[] = {
        {"", false},       {"123", true},     {"3.14", true},  {"总分 3", true},
        {"3 \t\r\n", true}, {"你好", false},   {"你好3", true}, {"hello", false},
        {"，。", false},    {"300米", false},  {"a", false},
    };
    for (const auto &[text, expected] : cases) {
        if (wetype::endsWithDigit(text) != expected)
            throw std::runtime_error("wrong digit classification");
    }
    // Invalid UTF-8 must not be read as a digit: continuation bytes are
    // 0x80-0xBF, so a CJK character can never end in an ASCII digit byte.
    if (wetype::endsWithDigit(std::string_view("\xE4\xBD", 2)))
        throw std::runtime_error("truncated UTF-8 read as a digit");
    if (wetype::endsWithDigit(std::string_view("中\xF0\x9F", 4)))
        throw std::runtime_error("invalid trailing sequence read as a digit");
    if (!wetype::endsWithDigit("中\xE4\xB8\xAD" "7"))
        throw std::runtime_error("digit after a CJK character should count");
}

}  // namespace

int main() {
    try {
        expectTable();
        expectOwnedSetIsClosed();
        expectDigitException();
        std::cout << "PASS punctuation: width table, owned key set, digit exception\n";
    } catch (const std::exception &error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
    return 0;
}
