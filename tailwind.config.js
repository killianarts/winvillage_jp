/** @type {import('tailwindcss').Config} */
const plugin = require("tailwindcss/plugin");
const {spawnSync} = require("child_process");

// Calls Django to fetch template files
const getTemplateFiles = () => {
    const command = "python3";
    const args = ["manage.py", "tailwind", "list_templates"];
    // Assumes tailwind.config.js is located in the BASE_DIR of your Django project.
    const options = {cwd: __dirname};

    const result = spawnSync(command, args, options);

    if (result.error) {
        throw result.error;
    }

    if (result.status !== 0) {
        console.log(result.stdout.toString(), result.stderr.toString());
        throw new Error(
            `Django management command exited with code ${result.status}`
        );
    }

    const templateFiles = result.stdout
        .toString()
        .split("\n")
        .map((file) => file.trim())
        .filter(function (e) {
            return e;
        }); // Remove empty strings, including last empty line.
    return templateFiles;
};

module.exports = {
    content: [].concat(getTemplateFiles()),
    theme: {
        extend: {
            dropShadow: {
                'hard-45-2xs': '1px 1px 0 rgba(0, 0, 0, 0.2)',
                'hard-45-xs': '3px 3px 0 rgba(0, 0, 0, 0.2)',
                'hard-45-sm': '5px 5px 0 rgba(0, 0, 0, 0.2)',
                'hard-45-md': '7px 7px 0 rgba(0, 0, 0, 0.2)',
                'hard-45-lg': '10px 10px 0 rgba(0, 0, 0, 0.2)',
                'hard-45-xl': '15px 15px 0 rgba(0, 0, 0, 0.2)',
                'hard-45-2xl': '20px 20px 0 rgba(0, 0, 0, 0.2)',
            },
            spacing: {
                "128": '32rem',
            },
            maxWidth: {
                "screen-2xl": '1500px',
            },
            fontFamily: {
                'system-ui': ["system-ui", "sans-serif"],
                handwritten: ['"Segoe Print"', '"Bradley Hand"', "Chilanka", "TSCu_Comic", "casual", "cursive"],
                code: ["ui-monospace", '"Cascadia Code"', '"Source Code Pro"', "Menlo", "Consolas", '"DejaVu Sans Mono"', "monospace"], // for backwards compatibility
                'monospace-code': ["ui-monospace", '"Cascadia Code"', '"Source Code Pro"', "Menlo", "Consolas", '"DejaVu Sans Mono"', "monospace"],
                industrial: ["Bahnschrift", 'DIN Alternate', 'Franklin Gothic Medium', 'Nimbus Sans Narrow', "sans-serif-condensed", "sans-serif"],
                antique: ["Superclarendon", 'Bookman Old Style', 'URW Bookman', 'URW Bookman L', 'Georgia Pro', "Georgia", "serif"],
                transitional: ["Charter", 'Bitstream Charter', 'Sitka Text', "Cambria", "serif"],
                'old-style': ['Iowan Old Style', 'Palatino Linotype', 'URW Palladio L', "P052", "serif"],
                humanist: ["Seravek", 'Gill Sans Nova', "Ubuntu", "Calibri", 'DejaVu Sans', "source-sans-pro", "sans-serif"],
                'geometric-humanist': ["Avenir", "Montserrat", "Corbel", 'URW Gothic', "source-sans-pro", "sans-serif"],
                'classical-humanist': ["Optima", "Candara", 'Noto Sans', "source-sans-pro", "sans-serif"],
                'neo-grotesque': ["Inter", "Roboto", 'Helvetica Neue', 'Arial Nova', 'Nimbus Sans', "Arial", "sans-serif"],
                'monospace-slab-serif': ['Nimbus Mono PS', 'Courier New', "monospace"],

            }
        },
        borderWidth: {
            DEFAULT: '1px',
            '0': '0',
            '2': '2px',
            '3': '3px',
            '4': '4px',
            '6': '6px',
            '8': '8px',
        },
        fontFamily: {
            sans: ['"Hiragino Sans"', "Meiryo", 'sans-serif'],
            serif: ['"Hiragino Mincho Pro"', '"Yu Mincho"','serif']
        }
    },
    plugins: [
        require("@tailwindcss/typography"),
        require("@tailwindcss/forms"),
        require("@tailwindcss/aspect-ratio"),
        require("@tailwindcss/container-queries"),
        plugin(function ({addVariant}) {
            addVariant("htmx-settling", ["&.htmx-settling", ".htmx-settling &"]);
            addVariant("htmx-request", ["&.htmx-request", ".htmx-request &"]);
            addVariant("htmx-swapping", ["&.htmx-swapping", ".htmx-swapping &"]);
            addVariant("htmx-added", ["&.htmx-added", ".htmx-added &"]);
        }),
    ],
};
