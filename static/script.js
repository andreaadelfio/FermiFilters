$(function() {
    // Inizializza gli slider
    for (const [col, info] of Object.entries(Object.assign({}, info_dict_ft2, info_dict_ft1))) {
        $(`#${col}_slider`).slider({
            range: true,
            min: info.min,
            max: info.max,
            values: [info.min, info.max],
            step: getResolution(info),
            slide: function(event, ui) {
                $(`#${col}_min`).val(ui.values[0]);
                $(`#${col}_max`).val(ui.values[1]);
                $(`#${col}_min_val`).text(ui.values[0]);
                $(`#${col}_max_val`).text(ui.values[1]);
                updateFilterExpr();
            },
            change: function(event, ui) {
                updateFilterExpr();
            }
        });

        if (info.default == 1) {
            $(`.col-toggle[data-col="${col}"]`).prop('checked', true);
            $(`#${col}_slider`).closest('.slider-item').show();
        }

        if (info.disabled == 0) {
            $(`#${col}_slider`).slider('disable');
        }
        // Imposta i valori iniziali degli input nascosti e delle etichette
        $(`#${col}_min`).val(info.min);
        $(`#${col}_max`).val(info.max);
        $(`#${col}_min_val`).text(info.min);
        $(`#${col}_max_val`).text(info.max);
    }

    // Checkbox per mostrare/nascondere i singoli slider
    $('.col-toggle').on('change', function() {
        let colName = $(this).data('col');
        $(`#${colName}_slider`).closest('.slider-item').toggle(this.checked);
    });

    // Nascondi gli slider delle colonne non selezionate di default
    $('.col-toggle').each(function() {
        let colName = $(this).data('col');
        $(`#${colName}_slider`).closest('.slider-item').toggle(this.checked);
    });

    // Aggiorna con updateFilterExpr se cambia custom_filter
    $('#custom_filter').on('input', updateFilterExpr);

    $('#eclipticcut').on('change', function() {
        const isChecked = $(this).is(':checked');
        $('#eclipticradius').prop('disabled', !isChecked);
        $('#eclipticoperator').prop('disabled', !isChecked);
    });

    $('#sourcecut').on('change', function() {
        const isChecked = $(this).is(':checked');
        $('#ra').prop('disabled', !isChecked);
        $('#dec').prop('disabled', !isChecked);
        $('#radius').prop('disabled', !isChecked);
    });

    // Pulsante "Aggiorna Plot" => invio Ajax
    $('#apply-filters').on('click', function() {
        if (validateInputs()) {
            const filterExpr = $('#filter_expr').val();
            // const roicut = $('#roicut').is(':checked') ? 'on' : 'off';
            const select_dict = $('#ft1_filters_dict').val();
            const maketime_dict = $('#ft2_filters_dict').val();
            const ecliptic_cut_dict = $('#ecliptic_cut_dict').val();
            const update_plot = $('#update-plot-btn').is(':checked') ? 'on' : 'off';
            $.ajax({
                url: '/apply_filters',
                type: 'POST',
                data: {
                    maketime_dict: maketime_dict,
                    select_dict: select_dict,
                    ecliptic_cut_dict: ecliptic_cut_dict,
                    update_plot: update_plot
                },
                success: function(resp) {
                    if (resp.error) {
                        alert(resp.error);
                    } else {
                        if (resp.plot_url && update_plot === 'on') {
                            $('#plot-image').attr('src', resp.plot_url + '?' + new Date().getTime()).show();
                            $('#plot-box').html(`<img id="plot-image" src="${resp.plot_url + '?' + new Date().getTime()}" alt="Filtered Data Plot" style="max-width: 100%; max-height: 100%;">`);
                        } else {
                            $('#plot-box').html('<p>No available plot</p>');
                        }

                        let filtersApplied = [];
                        if (filterExpr) filtersApplied.push(`Filters: ${filterExpr}`);
                        // if (roicut === 'on') filtersApplied.push('ROI cut');

                        $('#filter-info-text').text(filtersApplied
                            ? filtersApplied.join(' | ')
                            : 'No filters applied');
                    }
                },
                error: function() {
                    alert('Error during plot update.');
                }
            });
        }
    });
});

function getResolution(info) {
    const difference = info.max - info.min;
    const decimalPlaces = countDecimalPlaces(difference);
    return Math.pow(10, -decimalPlaces);
}

function countDecimalPlaces(number) {
    if (Math.floor(number) === number) return 0;
    return number.toString().split(".")[1].length || 0;
}

function updateFilterExpr() {
    let filterExpr = [];
    let ft1_filters_dict = {};
    let ft2_filters_dict = {};
    let ecliptic_cut_dict = {};
    const radius = $('#radius').val();
    const dec = $('#dec').val();
    const ra = $('#ra').val();
    const sourcecut = $('#sourcecut').is(':checked');
    const roicut = $('#roicut').is(':checked');
    const eclipticcut = $('#eclipticcut').is(':checked');
    const eclipticradius = $('#eclipticradius').val();
    const eclipticoperator = $('#eclipticoperator').val();
    if (sourcecut && radius && dec && ra) {
        ft1_filters_dict.radius = radius;
        ft1_filters_dict.ra = ra;
        ft1_filters_dict.dec = dec;
    }
    if (roicut) ft2_filters_dict.roicut = roicut;
    if (eclipticcut && eclipticradius && eclipticoperator) {
        ecliptic_cut_dict.eclipticradius = eclipticradius;
        ecliptic_cut_dict.eclipticoperator = eclipticoperator;
    }
    for (const [col, info] of Object.entries(info_dict_ft2)) {
        let minVal = parseFloat($(`#${col}_min`).val());
        let maxVal = parseFloat($(`#${col}_max`).val());
        
        if (minVal !== info.min || maxVal !== info.max) {
            filterExpr.push(`(${col} >= ${minVal}) && (${col} <= ${maxVal})`);
        }
    }
    for (const [col, info] of Object.entries(info_dict_ft1)) {
        let minVal = parseFloat($(`#${col}_min`).val());
        let maxVal = parseFloat($(`#${col}_max`).val());
        if (minVal !== info.min || maxVal !== info.max) {
            ft1_filters_dict[col] = [minVal, maxVal];
        }
    }
    let customFilter = $('#custom_filter').val().trim();
    if (customFilter) filterExpr.push(customFilter);
    const finalExpr = filterExpr.join(' && ');
    $('#filter_expr').val(finalExpr);
    if (finalExpr !== '') ft2_filters_dict.filter_expr = finalExpr;
    $('#ft1_filters_dict').val(JSON.stringify(ft1_filters_dict));
    $('#ft2_filters_dict').val(JSON.stringify(ft2_filters_dict));
    $('#ecliptic_cut_dict').val(JSON.stringify(ecliptic_cut_dict));
    $('#filter-info-text').text(finalExpr.trim() ? 'Filters: ' + finalExpr : 'No filters applied');
}

function manualUpdateFilterExpr() {
    const manualFilterExpr = $('#filter_expr').val().trim();
    $('#filter-info-text').text(manualFilterExpr ? manualFilterExpr : 'No filters applied');
}

function resetSliders() {
    for (const [col, info] of Object.entries(Object.assign({}, info_dict_ft2, info_dict_ft1))) {
        $(`#${col}_slider`).slider('values', [info.min, info.max]);
        $(`#${col}_min`).val(info.min);
        $(`#${col}_max`).val(info.max);
        $(`#${col}_min_val`).text(info.min);
        $(`#${col}_max_val`).text(info.max);
    }
    $('#custom_filter').val('');
    $('#filter_expr').val('');
    $('#filter-info-text').text('No filters applied');
    $('#roicut').prop('checked', false);
    $('#zenith_angle').val('');
    $('#radius').val('');
    $('#ra').val('');
    $('#dec').val('');
    $('#ft1_filters_dict').val('{}');
}

function resetDefaultColumns() {
    $('.col-toggle').prop('checked', false);
    $('.slider-item').hide();
    for (const [col, info] of Object.entries(Object.assign({}, info_dict_ft2, info_dict_ft1))) {
        if (info.default == 1) {
            $(`.col-toggle[data-col="${col}"]`).prop('checked', true);
            $(`#${col}_slider`).closest('.slider-item').show();
        }
    }
}

function validateInputs() {
    let isValid = true;
    let errorMessage = '';
    const sourcecut = document.getElementById('sourcecut').checked;
    if (sourcecut) {
        const raInput = document.getElementById('ra');
        const decInput = document.getElementById('dec');
        const radiusInput = document.getElementById('radius');
        
        const ra = raInput && raInput.value ? parseFloat(raInput.value) : NaN;
        const dec = decInput && decInput.value ? parseFloat(decInput.value) : NaN;
        const radius = radiusInput && radiusInput.value ? parseFloat(radiusInput.value) : NaN;

        let isValid = !isNaN(ra) && !isNaN(dec) && !isNaN(radius);
        if (!isValid) {
            errorMessage = 'Please fill in all required fields.\n';
        } else {
            errorMessage = '';
            // Validate RA (0 to 360 degrees)
            if (isNaN(ra) || ra < 0 || ra > 360) {
                isValid = false;
                errorMessage += 'RA must be a number between 0 and 360.\n';
            }
            
            // Validate DEC (-90 to 90 degrees)
            if (isNaN(dec) || dec < -90 || dec > 90) {
                isValid = false;
                errorMessage += 'DEC must be a number between -90 and 90.\n';
            }
            
            // Validate Radius (positive number)
            if (isNaN(radius) || radius <= 0) {
                isValid = false;
                errorMessage += 'Radius must be a positive number.\n';
            }
        }
        console.log(isValid, errorMessage);
        if (!isValid) {
            alert(errorMessage);
        }
    }
    
    const eclipticcut = document.getElementById('eclipticcut').checked;
    if (eclipticcut) {
        let errorMessage = '';
        const eclipticradiusInput = document.getElementById('eclipticradius');

        const eclipticradius = eclipticradiusInput && eclipticradiusInput.value ? parseFloat(eclipticradiusInput.value) : NaN;

        if (isNaN(eclipticradius) || eclipticradius <= 0) {
            isValid = false;
            errorMessage += 'Ecliptic radius must be a positive number.\n';
        }
        if (!isValid) {
            alert(errorMessage);
        }
    }

    return isValid;
}