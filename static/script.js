document.addEventListener('DOMContentLoaded', function() {
    const table = new Tabulator("#stock-table", {
        layout: "fitData",  // Fit columns to table width
        pagination: "local",  // Enable client-side pagination
        paginationSize: 20,  // Number of rows per page
        paginationSizeSelector: [20, 50, 75, 100],  // Dropdown to select rows per page+
        ajaxURL: "/get_initial_data",  // URL to fetch the initial data
        initialSort: [{ column: "Market Cap", dir: "desc" }],  // Sort by Market Cap in descending order by default
        columns: [
            { title: "Ticker", field: "Ticker", frozen: true },
            {
                title: "Market Cap",
                field: "Market Cap",
                sorter: "number",  // Sort as a numeric value
                formatter: marketCapFormatter,  // Custom formatter for Market Cap with $ sign and abbreviations
            },
            { title: "PE Ratio", field: "PE Ratio", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "Forward P/E", field: "Forward P/E", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "P/S Ratio", field: "P/S Ratio", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "P/B Ratio", field: "P/B Ratio", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "Dividend Yield (%)", field: "Dividend Yield (%)", sorter: "number", formatter: percentageFormatter },
            { title: "Current Ratio", field: "Current Ratio", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "Debt/Equity", field: "Debt/Equity", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "Revenue Growth 4Y (%)", field: "Revenue Growth 4Y (%)", sorter: "number", formatter: percentageFormatter },
            { title: "EPS Growth 4Y (%)", field: "EPS Growth 4Y (%)", sorter: "number", formatter: percentageFormatter },
            { title: "Forward EPS Growth (%)", field: "Forward EPS Growth (%)", sorter: "number", formatter: percentageFormatter },
            { title: "EPS", field: "EPS", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "PEG Ratio", field: "PEG Ratio", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "ROE (%)", field: "ROE (%)", sorter: "number", formatter: percentageFormatter },
            { title: "ROA (%)", field: "ROA (%)", sorter: "number", formatter: percentageFormatter },
            { title: "ROIC (%)", field: "ROIC (%)", sorter: "number", formatter: percentageFormatter },
            { title: "Profit Margin (%)", field: "Profit Margin (%)", sorter: "number", formatter: percentageFormatter },
            { title: "Gross Margin (%)", field: "Gross Margin (%)", sorter: "number", formatter: percentageFormatter },
            { title: "FCF Yield (%)", field: "FCF Yield (%)", sorter: "number", formatter: percentageFormatter },
            { title: "FCF/EV", field: "FCF/EV", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            { title: "EV/EBITDA", field: "EV/EBITDA", sorter: "number", formatter: "money", formatterParams: { thousand: ",", precision: 2 } },
            {
                title: "Recent 52-Week High",
                field: "Recent 52-Week High",
                sorter: "boolean",
                formatter: "tickCross"
            },
            { title: "Sector", field: "Sector", sorter: "string" },
            { title: "Industry", field: "Industry", sorter: "string" }
        ]
    });

    // Fetch sectors and populate the Sector dropdown without Choices.js
    const sectorSelect = document.getElementById('sector');

    fetch('/get_sectors')
        .then(response => response.json())
        .then(sectors => {
            console.log("Sectors received:", sectors);  // Log the received sector data

            // Sort sectors alphabetically
            sectors.sort();

            // Clear any existing options in the select dropdown
            sectorSelect.innerHTML = '';

            // Add a default "Any" option
            const defaultOption = document.createElement('option');
            defaultOption.value = "";
            defaultOption.textContent = "Any";
            sectorSelect.appendChild(defaultOption);

            // Populate the dropdown with the received sectors
            sectors.forEach(sector => {
                const option = document.createElement('option');
                option.value = sector;
                option.textContent = sector;
                sectorSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching sectors:', error));

        // Populate the Industry dropdown
    const industrySelect = document.getElementById('industry');

    fetch('/get_industries')
        .then(response => {
            console.log("Response received:", response);  // Log the full response
            return response.json();  // Convert response to JSON
        })
        .then(industries => {
            console.log("Industries received:", industries);  // Log the received industry data

            // Sort industries alphabetically
            industries.sort();

            industrySelect.innerHTML = '';  // Clear any existing options

            // Add "Any" option at the top
            const anyOption = document.createElement('option');
            anyOption.value = "Any";
            anyOption.text = "Any";
            industrySelect.appendChild(anyOption);

            // Add the fetched industry options
            industries.forEach(industry => {
                const option = document.createElement('option');
                option.value = industry;
                option.text = industry;
                industrySelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching industries:', error));

    // Custom formatter for Market Cap with $ sign, abbreviations, and comma formatting
    function marketCapFormatter(cell, formatterParams, onRendered) {
        let value = cell.getValue();
        if (value === "N/A") {
            return value;
        } else if (value >= 1e9) {
            return `$${(value / 1e9).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}B`;
        } else if (value >= 1e6) {
            return `$${(value / 1e6).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M`;
        } else {
            return `$${value.toLocaleString()}`;
        }
    }

    // Custom formatter to add percentage symbol
    function percentageFormatter(cell, formatterParams, onRendered) {
        let value = cell.getValue();
        return value !== "N/A" ? `${parseFloat(value).toFixed(2)}%` : value;
    }
    // Convert formatted Market Cap input (e.g., 1,500.5B or 1,000M) to a numeric value
    function parseMarketCapInput(value) {
        if (!value) return null;

        value = value.trim().toUpperCase();  // Handle case-insensitive input for B/M

        if (value.endsWith("B")) {
            return parseFloat(value.replace(/,/g, '').slice(0, -1)) * 1e9;
        } else if (value.endsWith("M")) {
            return parseFloat(value.replace(/,/g, '').slice(0, -1)) * 1e6;
        } else {
            return parseFloat(value.replace(/,/g, ''));
        }
    }

    // Function to apply filters and update the table
    document.getElementById('filter_data').addEventListener('click', function() {
        const filters = {
            'Market Cap': [
                parseMarketCapInput(document.getElementById('marketCapMin').value),  // Handle formatted input
                parseMarketCapInput(document.getElementById('marketCapMax').value)
            ],
            'PE Ratio': getMinMax('peMin', 'peMax'),
            'Forward P/E': getMinMax('forwardPeMin', 'forwardPeMax'),
            'P/S Ratio': getMinMax('psMin', 'psMax'),
            'P/B Ratio': getMinMax('pbMin', 'pbMax'),
            'Dividend Yield (%)': getMinMax('dividendYieldMin', 'dividendYieldMax'),
            'Current Ratio': getMinMax('currentRatioMin', 'currentRatioMax'),
            'Debt/Equity': getMinMax('debtEquityMin', 'debtEquityMax'),
            'Revenue Growth 4Y (%)': getMinMax('revenueGrowthMin', 'revenueGrowthMax'),
            'EPS Growth 4Y (%)': getMinMax('epsGrowthMin', 'epsGrowthMax'),
            'Forward EPS Growth (%)': getMinMax('forwardEpsGrowthMin', 'forwardEpsGrowthMax'),
            'EPS': getMinMax('epsMin', 'epsMax'),
            'PEG Ratio': getMinMax('pegMin', 'pegMax'),
            'ROE (%)': getMinMax('roeMin', 'roeMax'),
            'ROA (%)': getMinMax('roaMin', 'roaMax'),
            'ROIC (%)': getMinMax('roicMin', 'roicMax'),
            'Profit Margin (%)': getMinMax('profitMarginMin', 'profitMarginMax'),
            'Gross Margin (%)': getMinMax('grossMarginMin', 'grossMarginMax'),
            'FCF Yield (%)': getMinMax('fcfYieldMin', 'fcfYieldMax'),
            'FCF/EV': getMinMax('fcfEvMin', 'fcfEvMax'),
            'EV/EBITDA': getMinMax('evEbitdaMin', 'evEbitdaMax'),
            'Recent 52-Week High': mapRecent52WeekHigh(document.getElementById('recent52WeekHigh').value),
            'Sector': document.getElementById('sector').value !== "Any" ? document.getElementById('sector').value : null,
            'Industry': document.getElementById('industry').value !== "Any" ? document.getElementById('industry').value : null
        };

        console.log("Filters to be sent to backend:", filters);

        fetch('/filter_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(filters)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Filtered data received from server:", data);
            table.setData(data);  // Update the table with the filtered data
        })
        .catch(error => console.error('Error:', error));
    });
        // Export to CSV functionality
    document.getElementById('export_csv').addEventListener('click', function() {
        table.download("csv", "filtered_data.csv");  // Exports the table data as CSV
    });

    document.getElementById('reset_filters').addEventListener('click', function() {
        // Capture the current page size
        const currentPageSize = table.getPageSize();

        // Reset all input fields (number and text)
        document.querySelectorAll('input[type="number"], input[type="text"]').forEach(input => {
            input.value = '';  // Clear the value of the number and text inputs
        });

        // Reset all dropdowns to their default value (for example, "Any")
        document.querySelectorAll('select').forEach(select => {
            select.value = 'Any';  // Set all selects to the default "Any" value
        });

        // Reload the table with unfiltered data
        table.setData("/get_initial_data").then(function() {
            // Restore the previously selected page size after the table reloads
            table.setPageSize(currentPageSize);
        });
    });

    // Helper function to get min and max values from input fields
    function getMinMax(minId, maxId) {
        const minValueElement = document.getElementById(minId);
        const maxValueElement = document.getElementById(maxId);

        const minValue = minValueElement && minValueElement.value ? parseFloat(minValueElement.value) : null;
        const maxValue = maxValueElement && maxValueElement.value ? parseFloat(maxValueElement.value) : null;

        return [minValue, maxValue];
    }

    // Function to map the "Recent 52-Week High" dropdown
    function mapRecent52WeekHigh(value) {
        if (value === "Yes") {
            return true;
        } else if (value === "No") {
            return false;
        } else {
            return null;  // "Any" or empty will return null, meaning no filter is applied
        }
    }
});
