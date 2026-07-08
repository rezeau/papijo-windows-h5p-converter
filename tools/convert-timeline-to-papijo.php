<?php
declare(strict_types=1);

/**
 * Convert H5P Timeline default content.json structure
 * to Timeline Papi Jo content.json structure.
 *
 * Usage:
 *   php convert-timeline-to-papijo.php content_pretty.json content_converted.json
 */

const ADVANCED_TEXT_LIBRARY = 'H5P.AdvancedTextPapiJo 1.1';
const SIMPLE_TEXTAREA_LIBRARY = 'H5P.SimpleTextareaPapiJo 1.0';

$inputFile  = $argv[1] ?? 'content_pretty.json';
$outputFile = $argv[2] ?? 'content_converted.json';

/**
 * Options / defaults used when the original Timeline file
 * has no equivalent Papi Jo field.
 */
$options = [
    'defaultLayout' => 'right',
    'defaultBackgroundColor' => '#757575',

    'behaviour' => [
        'scalingMode' => 'human',
        'initialZoom' => 2,
        'timenavPosition' => 'bottom',
        'startatend' => false,
        'startatslide' => 1,
    ],

    // Set to null to keep the source Timeline language.
    // Set to 'en' if you want to force English.
    'forceLanguage' => null,

    // Timeline Papi Jo examples include an empty customQuote object.
    // Keep true unless your library accepts it being absent.
    'includeEmptyCustomQuote' => true,
];

if (!is_file($inputFile)) {
    fwrite(STDERR, "Input file not found: {$inputFile}\n");
    exit(1);
}

$rawJson = file_get_contents($inputFile);

if ($rawJson === false) {
    fwrite(STDERR, "Could not read input file: {$inputFile}\n");
    exit(1);
}

$source = json_decode($rawJson, true);

if (!is_array($source)) {
    fwrite(STDERR, "Invalid JSON in {$inputFile}: " . json_last_error_msg() . "\n");
    exit(1);
}

if (!isset($source['timeline']) || !is_array($source['timeline'])) {
    fwrite(STDERR, "This does not look like a default Timeline content file: missing timeline object.\n");
    exit(1);
}

$timeline = $source['timeline'];

$result = [
    'showTitleSlide' => true,
    'titleSlide' => mapTitleSlide($timeline, $options),
    'timelineItems' => mapTimelineItems($timeline['date'] ?? [], $options),
    'behaviour' => $options['behaviour'],
    'language' => $options['forceLanguage'] ?? ($timeline['language'] ?? 'en'),
];

$eras = mapEras($timeline['era'] ?? []);

if (!empty($eras)) {
    $result['eras'] = $eras;
}

$encoded = json_encode(
    $result,
    JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE
);

if ($encoded === false) {
    fwrite(STDERR, "Could not encode converted JSON: " . json_last_error_msg() . "\n");
    exit(1);
}

file_put_contents($outputFile, $encoded . PHP_EOL);

echo "Converted file written to: {$outputFile}\n";


/**
 * Map the default Timeline title data to the Papi Jo titleSlide object.
 */
function mapTitleSlide(array $timeline, array $options): array
{
    $asset = isset($timeline['asset']) && is_array($timeline['asset'])
        ? $timeline['asset']
        : [];

    $titleSlide = [
        'slideType' => 'title',
        'description' => makeAdvancedText($timeline['text'] ?? ''),
        'layout' => $options['defaultLayout'],
        'mediaType' => 'custom',
        'appearance' => makeAppearance($options),
        'title' => (string)($timeline['headline'] ?? ''),
    ];

    $info = makeInfo($asset);

    if ($info !== null) {
        $titleSlide['info'] = $info;
    }

    if (!empty($asset['media'])) {
        /*
         * Default Timeline uses external URLs.
         * Timeline Papi Jo regular slides use customMedia for URLs.
         * This script uses the same pattern for the title slide.
         *
         * If your Timeline Papi Jo title slide does not accept customMedia,
         * remove this field and add the title image manually in the editor.
         */
        $titleSlide['customMedia'] = (string)$asset['media'];
    }

    return $titleSlide;
}


/**
 * Map default Timeline date[] entries to Papi Jo timelineItems[].
 */
function mapTimelineItems(array $dates, array $options): array
{
    $items = [];

    foreach ($dates as $date) {
        if (!is_array($date)) {
            continue;
        }

        $asset = isset($date['asset']) && is_array($date['asset'])
            ? $date['asset']
            : [];

        $item = [
            'slideType' => 'regular',
            'TextOrImage' => 'text',
            'description' => makeAdvancedText($date['text'] ?? ''),
            'layout' => $options['defaultLayout'],
            'mediaType' => 'custom',
        ];

        if ($options['includeEmptyCustomQuote']) {
            $item['customQuote'] = makeSimpleTextarea();
        }

        $info = makeInfo($asset);

        if ($info !== null) {
            $item['info'] = $info;
        }

        $item['appearance'] = makeAppearance($options);

        if (isset($date['headline'])) {
            $item['title'] = (string)$date['headline'];
        }

        $startDate = normalizeDateValue($date['startDate'] ?? null);
        $endDate = normalizeDateValue($date['endDate'] ?? null);

        if ($startDate !== null) {
            $item['startDate'] = $startDate;
        }

        if ($endDate !== null) {
            $item['endDate'] = $endDate;
        }

        if (!empty($asset['media'])) {
            $item['customMedia'] = (string)$asset['media'];
        }

        $items[] = $item;
    }

    return $items;
}


/**
 * Map default Timeline era[] entries to Papi Jo eras[].
 *
 * Papi Jo example only keeps:
 * - name
 * - startDate
 * - endDate
 *
 * Default Timeline era text and tag are therefore not mapped.
 */
function mapEras(array $eras): array
{
    $mapped = [];

    foreach ($eras as $era) {
        if (!is_array($era)) {
            continue;
        }

        $item = [];

        if (isset($era['headline'])) {
            $item['name'] = (string)$era['headline'];
        }

        $startDate = normalizeDateValue($era['startDate'] ?? null);
        $endDate = normalizeDateValue($era['endDate'] ?? null);

        if ($startDate !== null) {
            $item['startDate'] = $startDate;
        }

        if ($endDate !== null) {
            $item['endDate'] = $endDate;
        }

        if (!empty($item)) {
            $mapped[] = $item;
        }
    }

    return $mapped;
}


/**
 * Build an H5P.AdvancedTextPapiJo field.
 */
function makeAdvancedText(?string $html): array
{
    return [
        'params' => [
            'text' => normalizeHtml($html ?? ''),
        ],
        'library' => ADVANCED_TEXT_LIBRARY,
        'subContentId' => uuidV4(),
        'metadata' => [
            'contentType' => 'Text Papi Jo',
            'license' => 'U',
            'title' => 'Untitled Text Papi Jo',
        ],
    ];
}


/**
 * Build an empty H5P.SimpleTextareaPapiJo field.
 */
function makeSimpleTextarea(): array
{
    return [
        'params' => new stdClass(),
        'library' => SIMPLE_TEXTAREA_LIBRARY,
        'subContentId' => uuidV4(),
        'metadata' => [
            'contentType' => 'Simple Textarea Papi Jo',
            'license' => 'U',
        ],
    ];
}


/**
 * Build the Papi Jo appearance object.
 */
function makeAppearance(array $options): array
{
    return [
        'backgroundType' => 'none',
        'backgroundColor' => $options['defaultBackgroundColor'],
    ];
}


/**
 * Map asset credit/caption to Papi Jo info.
 */
function makeInfo(array $asset): ?array
{
    $credit = trim((string)($asset['credit'] ?? ''));
    $caption = trim((string)($asset['caption'] ?? ''));

    if ($credit === '' && $caption === '') {
        return null;
    }

    return [
        'credit' => htmlBlock($credit),
        'caption' => htmlBlock($caption),
    ];
}


/**
 * Convert default Timeline dates to Timeline Papi Jo dates.
 *
 * Default Timeline may use:
 *   YYYY
 *   YYYY,MM
 *   YYYY,MM,DD
 *
 * Timeline Papi Jo expects:
 *   YYYY
 *   YYYY-MM
 *   YYYY-MM-DD
 *
 * Also avoids returning empty strings, which would fail H5P semantics validation.
 */
function normalizeDateValue($value): ?string
{
    $value = trim((string)($value ?? ''));

    if ($value === '') {
        return null;
    }

    // Convert comma-separated date parts to hyphen-separated date parts.
    // Example: 2000,5,31 becomes 2000-5-31.
    $value = preg_replace('/\s*,\s*/', '-', $value);

    // Remove accidental spaces around hyphens.
    $value = preg_replace('/\s*-\s*/', '-', $value);

    return $value;
}


/**
 * Wrap plain text as a div, but leave existing HTML blocks alone.
 */
function htmlBlock(string $value): string
{
    $value = trim($value);

    if ($value === '') {
        return '';
    }

    if (preg_match('~^\s*<(div|p|blockquote|ul|ol|figure|table|h[1-6])\b~i', $value)) {
        return $value;
    }

    return '<div>' . $value . '</div>';
}


/**
 * Small cleanup for text fields.
 *
 * The original Timeline file often contains:
 * - trailing newlines
 * - empty divs
 * - divs where Papi Jo AdvancedText commonly uses p
 */
function normalizeHtml(string $html): string
{
    $html = trim($html);

    if ($html === '') {
        return '';
    }

    // Remove empty divs/paragraphs.
    $html = preg_replace('~<div>\s*(?:&nbsp;)?\s*</div>~iu', '', $html);
    $html = preg_replace('~<p>\s*(?:&nbsp;)?\s*</p>~iu', '', $html);

    // Convert div blocks to p blocks, matching your Papi Jo example.
    $html = preg_replace('~<div\b([^>]*)>~i', '<p$1>', $html);
    $html = preg_replace('~</div>~i', '</p>', $html);

    // Remove newlines between HTML blocks.
    $html = preg_replace("~\s*\R+\s*~u", '', $html);

    return trim($html);
}


/**
 * Generate a UUID v4 for H5P subContentId.
 */
function uuidV4(): string
{
    $data = random_bytes(16);

    $data[6] = chr((ord($data[6]) & 0x0f) | 0x40);
    $data[8] = chr((ord($data[8]) & 0x3f) | 0x80);

    return vsprintf(
        '%s%s-%s-%s-%s-%s%s%s',
        str_split(bin2hex($data), 4)
    );
}