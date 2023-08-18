"""
Code to analyse VASP defect calculations.

These functions are built from a combination of useful modules from pymatgen
and AIDE (by Adam Jackson and Alex Ganose), alongside substantial modification,
in the efforts of making an efficient, user-friendly package for managing and
analysing defect calculations, with publication-quality outputs.
"""
import os
import warnings
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps, ticker
from pymatgen.util.string import latexify
from shakenbreak.plotting import _format_defect_name


# TODO: Make a specific tutorial in docs for editing return Matplotlib figures, or with rcParams,
#  or with a stylesheet
# TODO: Add option to only plot defect states that are stable at some point in the bandgap
# TODO: Add option to plot formation energies at the centroid of the chemical stability region? And make
#  this the default if no chempots are specified? Or better default to plot both the most (
#  most-electronegative-)anion-rich and the (most-electropositive-)cation-rich chempot limits?
def formation_energy_plot(
    defect_phase_diagram,
    chempots: Optional[Dict] = None,
    facets: Optional[Union[List, str]] = None,
    elt_refs: Optional[Dict] = None,
    chempot_table: bool = True,
    all_entries: Union[bool, str] = False,
    style_file: Optional[str] = None,
    xlim: Optional[Tuple] = None,
    ylim: Optional[Tuple] = None,
    fermi_level: Optional[float] = None,
    colormap: str = "Dark2",
    auto_labels: bool = False,
    filename: Optional[str] = None,
):
    """
    Produce a defect formation energy vs Fermi level plot (a.k.a. a defect
    formation energy / transition level diagram). Returns the Matplotlib Figure
    object to allow further plot customisation.

    Args:
        defect_phase_diagram (DefectPhaseDiagram):
            DefectPhaseDiagram for which to plot defect formation energies
            (typically created from analysis.dpd_from_defect_dict).
        chempots (dict):
            Dictionary of chemical potentials to use for calculating the defect
            formation energies. This can have the form of
            {"facets": [{'facet': [chempot_dict]}]} (the format generated by
            doped's chemical potential parsing functions (see tutorials)) and
            facet(s) (chemical potential limit(s)) to plot can be chosen using
            `facets`, or a dictionary of **DFT**/absolute chemical potentials
            (not formal chemical potentials!), in the format:
            {element symbol: chemical potential} - if manually specifying
            chemical potentials this way, you can set the elt_refs option with
            the DFT reference energies of the elemental phases in order to show
            the formal (relative) chemical potentials above the plot.
            (Default: None)
        facets (list, str):
            A string or list of facet(s) (chemical potential limit(s)) for which
            to plot the defect formation energies, corresponding to 'facet' in
            {"facets": [{'facet': [chempot_dict]}]} (the format generated by
            doped's chemical potential parsing functions (see tutorials)). If
            not specified, will plot for each facet in `chempots`. (Default: None)
        elt_refs (dict):
            Dictionary of elemental reference energies for the chemical potentials
            in the format:
            {element symbol: reference energy} (to determine the formal chemical
            potentials, when chempots has been manually specified as
            {element symbol: chemical potential}). Unnecessary if chempots is
            provided in format generated by doped (see tutorials).
            (Default: None)
        chempot_table (bool):
            Whether to print the chemical potential table above the plot.
            (Default: True)
        all_entries (bool, str):
            Whether to plot the formation energy lines of _all_ defect entries,
            rather than the default of showing only the equilibrium states at each
            Fermi level position (traditional). If instead set to "faded", will plot
            the equilibrium states in bold, and all unstable states in faded grey
            (Default: False)
        style_file (str):
            Path to a mplstyle file to use for the plot. If None (default), uses
            the default doped style (from doped/utils/doped.mplstyle).
        xlim:
            Tuple (min,max) giving the range of the x-axis (Fermi level). May want
            to set manually when including transition level labels, to avoid crossing
            the axes. Default is to plot from -0.3 to +0.3 eV above the band gap.
        ylim:
            Tuple (min,max) giving the range for the y-axis (formation energy). May
            want to set manually when including transition level labels, to avoid
            crossing the axes. Default is from 0 to just above the maximum formation
            energy value in the band gap.
        fermi_level (float):
            If set, plots a dashed vertical line at this Fermi level value, typically
            used to indicate the equilibrium Fermi level position (e.g. calculated
            with py-sc-fermi). (Default: None)
        colormap (str): Colormap to use for the formation energy lines. (default: "Dark2")
        auto_labels (bool):
            Whether to automatically label the transition levels with their charge
            states. If there are many transition levels, this can be quite ugly.
            (Default: False)
        filename (str): Filename to save the plot to. (Default: None (not saved))

    Returns:
        Matplotlib Figure object.
    """
    # check input options:
    if all_entries not in [False, True, "faded"]:
        raise ValueError(f"`all_entries` option must be either False, True, or 'faded', not {all_entries}")

    if (
        chempots
        and facets is None
        and elt_refs is None
        and any(np.isclose(chempot, 0, atol=0.1) for chempot in chempots.values())
    ):
        # if any chempot is close to zero, this is likely a formal chemical potential and so inaccurate
        # here (trying to make this as idiotproof as possible to reduce unnecessary user queries...)
        warnings.warn(
            "At least one of your manually-specified chemical potentials is close to zero, "
            "which is likely a _formal_ chemical potential (i.e. relative to the elemental "
            "reference energies), but you have not specified the elemental reference "
            "energies with `elt_refs`. This will give large errors in the absolute values "
            "of formation energies, but the transition level positions will be unaffected."
        )

    style_file = style_file or f"{os.path.dirname(__file__)}/utils/doped.mplstyle"
    with plt.style.context(style_file):
        if chempots and "facets" in chempots:
            if facets is None:
                facets = chempots["facets"].keys()  # Phase diagram facets to use for chemical
                # potentials, to calculate and plot formation energies
            for facet in facets:
                dft_chempots = chempots["facets"][facet]
                elt_refs = chempots["elemental_refs"]
                plot_title = facet
                plot_filename = (
                    f"{filename.rsplit('.',1)[0]}_{facet}.{filename.rsplit('.',1)[1]}"
                    if filename
                    else None
                )

                plot = _TLD_plot(
                    defect_phase_diagram,
                    dft_chempots=dft_chempots,
                    elt_refs=elt_refs,
                    chempot_table=chempot_table,
                    all_entries=all_entries,
                    xlim=xlim,
                    ylim=ylim,
                    fermi_level=fermi_level,
                    title=plot_title,
                    colormap=colormap,
                    auto_labels=auto_labels,
                    filename=plot_filename,
                )

            return plot

        # Else if you only want to give {Elt: Energy} dict for chempots, or no chempots
        return _TLD_plot(
            defect_phase_diagram,
            dft_chempots=chempots,
            elt_refs=elt_refs,
            chempot_table=chempot_table,
            all_entries=all_entries,
            xlim=xlim,
            ylim=ylim,
            fermi_level=fermi_level,
            title=None,
            colormap=colormap,
            auto_labels=auto_labels,
            filename=filename,
        )


def _chempot_warning(dft_chempots):
    if dft_chempots is None:
        warnings.warn(
            "You have not specified chemical potentials (`chempots`), so chemical potentials are set to "
            "zero for each species. This will give large errors in the absolute values of formation "
            "energies, but the transition level positions will be unaffected."
        )


def _get_plot_setup(colormap, xy):
    cmap = colormaps[colormap]
    colors = cmap(np.linspace(0, 1, len(xy)))
    if colormap == "Dark2" and len(xy) >= 8:
        warnings.warn(
            f"The chosen colormap is Dark2, which only has 8 colours, yet you have {len(xy)} "
            f"defect species (so some defects will have the same line colour). Recommended to "
            f"change/set colormap to 'tab10' or 'tab20' (10 and 20 colours each)."
        )

    # generate plot:
    plt.clf()
    styled_fig_size = plt.rcParams["figure.figsize"]
    fig, ax = plt.subplots(figsize=((2.6 / 3.5) * styled_fig_size[0], (1.95 / 3.5) * styled_fig_size[1]))
    # Gives a final figure width matching styled_fig_size, with dimensions matching the doped default
    styled_font_size = plt.rcParams["font.size"]
    styled_linewidth = plt.rcParams["lines.linewidth"]
    styled_markersize = plt.rcParams["lines.markersize"]

    return cmap, colors, fig, ax, styled_fig_size, styled_font_size, styled_linewidth, styled_markersize


def _plot_formation_energy_lines(
    xy,
    colors,
    ax,
    styled_linewidth,
    styled_markersize,
    alpha=1.0,
):
    defect_names_for_legend = []
    for cnt, def_name in enumerate(xy.keys()):  # plot formation energy lines
        ax.plot(
            xy[def_name][0],
            xy[def_name][1],
            color=colors[cnt],
            markeredgecolor=colors[cnt],
            lw=styled_linewidth * 1.2,
            markersize=styled_markersize * (4 / 6),
            alpha=alpha,
        )
        defect_names_for_legend.append(def_name.split("@")[0])

    return defect_names_for_legend


def _add_band_edges_and_axis_limits(ax, band_gap, xlim, ylim, fermi_level=None):
    ax.imshow(
        [(0, 1), (0, 1)],
        cmap=plt.cm.Blues,
        extent=(xlim[0], 0, ylim[0], ylim[1]),
        vmin=0,
        vmax=3,
        interpolation="bicubic",
        rasterized=True,
        aspect="auto",
    )

    ax.imshow(
        [(1, 0), (1, 0)],
        cmap=plt.cm.Oranges,
        extent=(band_gap, xlim[1], ylim[0], ylim[1]),
        vmin=0,
        vmax=3,
        interpolation="bicubic",
        rasterized=True,
        aspect="auto",
    )

    ax.set_xlim(xlim)
    ax.plot([xlim[0], xlim[1]], [0, 0], "k-")  # black dashed line for E_formation = 0 in case ymin < 0
    ax.set_ylim(ylim)

    if fermi_level is not None:
        ax.axvline(x=fermi_level, linestyle="-.", color="k")
    ax.set_xlabel("Fermi Level (eV)")
    ax.set_ylabel("Formation Energy (eV)")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(4))
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(2))
    ax.yaxis.set_major_locator(ticker.MaxNLocator(4))
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))


def _set_title_and_save_figure(ax, fig, title, chempot_table, filename, styled_font_size):
    if title:
        if chempot_table:
            ax.set_title(
                latexify(title),
                size=1.2 * styled_font_size,
                pad=28,
                fontdict={"fontweight": "bold"},
            )
        else:
            ax.set_title(latexify(title), size=styled_font_size, fontdict={"fontweight": "bold"})
    if filename is not None:
        fig.savefig(filename, bbox_inches="tight", dpi=600)


def _get_legends_txt(for_legend, all_entries=False):
    # get latex-like legend titles
    legends_txt = []
    for defect_entry_name in for_legend:
        try:  # Format defect name for title and axis labels
            defect_name = _format_defect_name(
                defect_species=defect_entry_name,
                include_site_num_in_name=False,
            )
            if not all_entries:
                defect_name = f"{defect_name.rsplit('^', 1)[0]}$"  # exclude charge

        except Exception:  # if formatting fails, just use the defect_species name
            defect_name = defect_entry_name

        # add subscript labels for different configurations of same defect species
        if defect_name in legends_txt:
            defect_name = _format_defect_name(
                defect_species=defect_entry_name,
                include_site_num_in_name=True,
            )
            if not all_entries:
                defect_name = f"{defect_name.rsplit('^', 1)[0]}$"  # exclude charge

        if defect_name in legends_txt:
            i = 1
            while defect_name in legends_txt:
                i += 1
                defect_name = f"{defect_name[:-3]}{chr(96 + i)}{defect_name[-3:]}"  # a, b c etc
        legends_txt.append(defect_name)

    return legends_txt


def _get_formation_energy_lines(defect_phase_diagram, dft_chempots, xlim):
    xy, all_lines_xy = {}, {}  # dict of {defect_name: [[x_vals],[y_vals]]}
    y_range_vals, all_entries_y_range_vals = (
        [],
        [],
    )  # for finding max/min values on y-axis based on x-limits
    lower_cap, upper_cap = -100, 100  # arbitrary values to extend lines to
    ymin = 0

    for defect_entry in defect_phase_diagram.entries:
        defect_entry_name = f"{defect_entry.name}_{defect_entry.charge_state}"
        all_lines_xy[defect_entry_name] = [[], []]
        for x_extrem in [lower_cap, upper_cap]:
            all_lines_xy[defect_entry_name][0].append(x_extrem)
            all_lines_xy[defect_entry_name][1].append(
                defect_phase_diagram._formation_energy(
                    defect_entry, chemical_potentials=dft_chempots, fermi_level=x_extrem
                )
            )
            all_entries_y_range_vals.extend(
                defect_phase_diagram._formation_energy(
                    defect_entry, chemical_potentials=dft_chempots, fermi_level=x_window
                )
                for x_window in xlim
            )

    for def_name, def_tl in defect_phase_diagram.transition_level_map.items():
        xy[def_name] = [[], []]

        if def_tl:
            org_x = sorted(def_tl.keys())
            # establish lower x-bound
            first_charge = max(def_tl[org_x[0]])
            for defect_entry in defect_phase_diagram.stable_entries[def_name]:
                if defect_entry.charge_state == first_charge:
                    form_en = defect_phase_diagram._formation_energy(
                        defect_entry, chemical_potentials=dft_chempots, fermi_level=lower_cap
                    )
                    fe_left = defect_phase_diagram._formation_energy(
                        defect_entry, chemical_potentials=dft_chempots, fermi_level=xlim[0]
                    )
            xy[def_name][0].append(lower_cap)
            xy[def_name][1].append(form_en)
            y_range_vals.append(fe_left)

            # iterate over stable charge state transitions
            for fl in org_x:
                charge = max(def_tl[fl])
                for defect_entry in defect_phase_diagram.stable_entries[def_name]:
                    if defect_entry.charge_state == charge:
                        form_en = defect_phase_diagram._formation_energy(
                            defect_entry, chemical_potentials=dft_chempots, fermi_level=fl
                        )
                xy[def_name][0].append(fl)
                xy[def_name][1].append(form_en)
                y_range_vals.append(form_en)

            # establish upper x-bound
            last_charge = min(def_tl[org_x[-1]])
            for defect_entry in defect_phase_diagram.stable_entries[def_name]:
                if defect_entry.charge_state == last_charge:
                    form_en = defect_phase_diagram._formation_energy(
                        defect_entry, chemical_potentials=dft_chempots, fermi_level=upper_cap
                    )
                    fe_right = defect_phase_diagram._formation_energy(
                        defect_entry, chemical_potentials=dft_chempots, fermi_level=xlim[1]
                    )
            xy[def_name][0].append(upper_cap)
            xy[def_name][1].append(form_en)
            y_range_vals.append(fe_right)

        else:  # no transition level -> only one stable charge state, add all_line_xy and extend
            # y_range_vals; means this is only a 1-pump (chmp) loop
            xy[def_name] = all_lines_xy[def_name.rsplit("@", 1)[0]]  # get xy from all_lines_xy
            defect_entry = defect_phase_diagram.stable_entries[def_name][0]
            y_range_vals.extend(
                defect_phase_diagram._formation_energy(
                    defect_entry, chemical_potentials=dft_chempots, fermi_level=x_window
                )
                for x_window in xlim
            )

        # if xy corresponds to a line below 0 for all x in (0, band_gap), warn!
        yvals = _get_in_gap_yvals(xy[def_name][0], xy[def_name][1], (0, defect_phase_diagram.band_gap))
        if all(y < 0 for y in yvals):  # Check if all y-values are below zero
            warnings.warn(
                f"All formation energies for {def_name.rsplit('@', 1)[0]} are below zero across the "
                f"entire band gap range. This is typically unphysical (see docs), and likely due to "
                f"mis-specification of chemical potentials (see docstrings and/or tutorials). "
            )
            ymin = min(ymin, *yvals)

    return (xy, y_range_vals), (all_lines_xy, all_entries_y_range_vals), ymin


def _get_ylim_from_y_range_vals(y_range_vals, ymin=0, auto_labels=False):
    window = max(y_range_vals) - min(y_range_vals)
    spacer = 0.1 * window
    ylim = (ymin, max(y_range_vals) + spacer)
    if auto_labels:  # need to manually set xlim or ylim if labels cross axes!!
        ylim = (ymin, max(y_range_vals) * 1.17) if spacer / ylim[1] < 0.145 else ylim
        # Increase y_limit to give space for transition level labels

    return ylim


def _get_in_gap_yvals(x_coords, y_coords, x_range):
    relevant_x = np.linspace(x_range[0], x_range[1], 100)  # x values in range
    return np.interp(relevant_x, x_coords, y_coords)  # y values in range


def _TLD_plot(
    defect_phase_diagram,
    dft_chempots=None,
    elt_refs=None,
    chempot_table=True,
    all_entries: Union[bool, str] = False,
    xlim=None,
    ylim=None,
    fermi_level=None,
    title=None,
    colormap="Dark2",
    auto_labels=False,
    filename=None,
):
    """
    Produce defect Formation energy vs Fermi energy plot
    Args:
        dft_chempots:
            a dictionary of {Element:value} giving the chemical
            potential of each element
        xlim:
            Tuple (min,max) giving the range of the x (fermi energy) axis. This may need to be
            set manually when including transition level labels, so that they don't cross the axes.
        ylim:
            Tuple (min,max) giving the range for the formation energy axis. This may need to be
            set manually when including transition level labels, so that they don't cross the axes.

    Returns:
        a matplotlib object.
    """
    _chempot_warning(dft_chempots)
    if xlim is None:
        xlim = (-0.3, defect_phase_diagram.band_gap + 0.3)

    (xy, y_range_vals), (all_lines_xy, all_entries_y_range_vals), ymin = _get_formation_energy_lines(
        defect_phase_diagram, dft_chempots, xlim
    )

    (
        cmap,
        colors,
        fig,
        ax,
        styled_fig_size,
        styled_font_size,
        styled_linewidth,
        styled_markersize,
    ) = _get_plot_setup(colormap, all_lines_xy if all_entries is True else xy)

    defect_names_for_legend = _plot_formation_energy_lines(  # plot formation energies and get legend names
        all_lines_xy if all_entries is True else xy,
        colors=colors,
        ax=ax,
        styled_linewidth=styled_linewidth,
        styled_markersize=styled_markersize,
    )

    if all_entries == "faded":  # Redo `for` loop so grey 'all_lines_xy' not included in legend
        _legend = _plot_formation_energy_lines(
            all_lines_xy,
            colors=[(0.8, 0.8, 0.8)] * len(all_lines_xy),
            ax=ax,
            styled_linewidth=styled_linewidth,
            styled_markersize=styled_markersize,
            alpha=0.5,
        )

    for cnt, def_name in enumerate(xy.keys()):  # plot transition levels
        x_trans: List[float] = []
        y_trans: List[float] = []
        tl_labels, tl_label_type = [], []
        for x_val, chargeset in defect_phase_diagram.transition_level_map[def_name].items():
            x_trans.append(x_val)
            y_trans.extend(
                defect_phase_diagram._formation_energy(
                    defect_entry,
                    chemical_potentials=dft_chempots,
                    fermi_level=x_val,
                )
                for defect_entry in defect_phase_diagram.stable_entries[def_name]
                if defect_entry.charge_state == chargeset[0]
            )
            tl_labels.append(
                rf"$\epsilon$({max(chargeset):{'+' if max(chargeset) else ''}}/"
                f"{min(chargeset):{'+' if min(chargeset) else ''}})"
            )
            tl_label_type.append("start_positive" if max(chargeset) > 0 else "end_negative")
        if x_trans:
            ax.plot(
                x_trans,
                y_trans,
                marker="o",
                color=colors[cnt],
                markeredgecolor=colors[cnt],
                lw=styled_linewidth * 1.2,
                markersize=styled_markersize * (4 / 6),
                fillstyle="full",
            )
            if auto_labels:
                for index, coords in enumerate(zip(x_trans, y_trans)):
                    text_alignment = "right" if tl_label_type[index] == "start_positive" else "left"
                    ax.annotate(
                        tl_labels[index],  # this is the text
                        coords,  # this is the point to label
                        textcoords="offset points",  # how to position the text
                        xytext=(0, 5),  # distance from text to points (x,y)
                        ha=text_alignment,  # horizontal alignment of text
                        size=styled_font_size * 0.9,
                        annotation_clip=True,
                    )  # only show label if coords in current axes

    ax.legend(
        _get_legends_txt(
            [defect_entry.name for defect_entry in defect_phase_diagram.entries]
            if all_entries is True
            else defect_names_for_legend,
            all_entries=all_entries,
        ),
        loc=2,
        bbox_to_anchor=(1, 1),
    )

    if ylim is None:
        ylim = _get_ylim_from_y_range_vals(
            all_entries_y_range_vals if all_entries is True else y_range_vals,
            ymin=ymin,
            auto_labels=auto_labels,
        )

    _add_band_edges_and_axis_limits(
        ax, defect_phase_diagram.band_gap, xlim, ylim, fermi_level=fermi_level
    )  # Show colourful band edges
    if chempot_table and dft_chempots:
        _plot_chemical_potential_table(ax, dft_chempots, loc="left", elt_refs=elt_refs)

    _set_title_and_save_figure(ax, fig, title, chempot_table, filename, styled_font_size)

    return fig


def _plot_chemical_potential_table(
    ax,
    dft_chempots,
    loc="left",
    elt_refs=None,
):
    if elt_refs is not None:
        dft_chempots = {elt: energy - elt_refs[elt] for elt, energy in dft_chempots.items()}
    labels = [rf"$\mathregular{{\mu_{{{s}}}}}$," for s in sorted(dft_chempots.keys())]
    labels[0] = f"({labels[0]}"
    labels[-1] = f"{labels[-1][:-1]})"  # [:-1] removes trailing comma
    labels = ["Chemical Potentials", *labels, " Units:"]

    text_list = [f"{dft_chempots[el]:.2f}," for el in sorted(dft_chempots.keys())]

    # add brackets to first and last entries:
    text_list[0] = f"({text_list[0]}"
    text_list[-1] = f"{text_list[-1][:-1]})"  # [:-1] removes trailing comma
    if elt_refs is not None:
        text_list = ["(wrt Elemental refs)", *text_list, "  [eV]"]
    else:
        text_list = ["(from calculations)", *text_list, "  [eV]"]
    widths = [0.1] + [0.9 / len(dft_chempots)] * (len(dft_chempots) + 2)
    tab = ax.table(cellText=[text_list], colLabels=labels, colWidths=widths, loc="top", cellLoc=loc)
    tab.auto_set_column_width(list(range(len(widths))))

    for cell in tab.get_celld().values():
        cell.set_linewidth(0)

    return tab
