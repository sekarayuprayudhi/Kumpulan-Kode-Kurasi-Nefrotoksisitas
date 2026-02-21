import glob, os, re
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def filter_excel_by_keyword(
    excel_files_pattern,
    list_sortir,
    column_name="Item Name",
    output_prefix="SC",
    output_suffix="Diuretik",
):
    """
    Filter Excel berdasarkan daftar nama parameter yang berbeda
    tapi memiliki konsep sama (exact matching, case-insensitive).
    """

    excel_files = glob.glob(excel_files_pattern)
    print(f"Found {len(excel_files)} Excel files.")

    # Normalisasi list ke lowercase untuk matching
    list_lower = {str(x).lower() for x in list_sortir}

    for file_path in excel_files:
        print(f"\nProcessing: {file_path}")

        df = pd.read_excel(file_path)

        if column_name not in df.columns:
            print(f"Kolom '{column_name}' tidak ditemukan. Skip.")
            continue

        # ===== Exact concept match (case-insensitive) =====
        mask = df[column_name].astype(str).str.lower().isin(list_lower)
        df_filtered = df[mask].copy()

        if df_filtered.empty:
            print("Tidak ada parameter cocok. Skip.")
            continue

        # ===== Ambil identifier dari nama file =====
        match = re.search(r'SC\s(.+?)\.xlsx', os.path.basename(file_path))
        if match:
            identifier = match.group(1).strip()
        else:
            identifier = os.path.splitext(os.path.basename(file_path))[0]

        new_file_name = f"D:/{output_prefix} {identifier} {output_suffix}.xlsx"

        df_filtered.to_excel(new_file_name, index=False)
        print(f"Menyimpan {len(df_filtered)} baris → '{new_file_name}'")

    print("\nSelesai.")

def load_and_combine_excel_data(glob_pattern: str, 
                                year: int = 2025,
                                ):
    
    excel_files = glob.glob(glob_pattern)
    df_list = []

    for file_path in excel_files:
        df = pd.read_excel(file_path)

        month = file_path.split(' ')[-3].replace('.xlsx', '')

        df['Bulan'] = month
        df['Tahun'] = file_path.split(' ')[-2].replace('.xlsx', '')

        df_list.append(df)

    df_combined = pd.concat(df_list, ignore_index=True)
    
    return df_combined

def patient_visit_frequency(
    df,
    patient_col="Patient Name",
    date_col="Order Date",
    date_format="%d/%m/%Y %H:%M:%S",
    plot=True
):
    """
    Menghitung distribusi frekuensi interval kunjungan pasien (hari & minggu).

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame berisi data kunjungan pasien.
    patient_col : str
        Kolom ID pasien (misal patient_id).
    date_col : str
        Kolom tanggal kunjungan.
    date_format : str
        Format datetime pada kolom tanggal.
  
    Returns
    -------
    intervals_df : pandas.DataFrame
        DataFrame interval antar kunjungan (hari & minggu).
    freq_days : pandas.Series
        Distribusi frekuensi interval (hari).
    freq_weeks : pandas.Series
        Distribusi frekuensi interval (mingguan, berbasis bin).
    """

    df = df.copy()

    # Pastikan datetime
    df[date_col] = pd.to_datetime(
        df[date_col],
        format=date_format,
        errors="coerce"
    )

    intervals_days = []
    intervals_weeks = []

    # Mengitung interval antar kunjungan per pasien
    for _, group in df.groupby(patient_col):
        dates = group[date_col].dropna().sort_values()

        if len(dates) < 2:
            continue

        deltas = dates.diff().dropna()
        intervals_days.append(deltas.dt.days.max())
        intervals_weeks.append(deltas.dt.days.max() / 7)

    intervals_df = pd.DataFrame({
        "interval_days": intervals_days,
        "interval_weeks": intervals_weeks
    })

    # Distribusi hari
    freq_days = intervals_df["interval_days"].value_counts().sort_index()

    # Bin mingguan 
    bins = [1, 2, 4, 8, 12, 24, 52, 1000]
    labels = [
        "1–2 minggu",
        "2–4 minggu",
        "1–2 bulan",
        "2–3 bulan",
        "3–6 bulan",
        "6–12 bulan",
        ">12 bulan"
    ]

    intervals_df["week_bin"] = pd.cut(
        intervals_df["interval_weeks"],
        bins=bins,
        labels=labels,
        right=False
    )

    freq_weeks = intervals_df["week_bin"].value_counts().sort_index()

    # Plot opsional
    if plot:
        # Histogram hari
        """plt.figure(figsize=(8, 5))
        plt.hist(intervals_df["interval_days"], bins=30, edgecolor="black")
        plt.xlabel("Interval Kunjungan (Hari)")
        plt.ylabel("Frekuensi")
        plt.title("Distribusi Interval Antar Kunjungan Pasien (Hari)")
        plt.grid(alpha=0.3)
        plt.show()"""

        # Bar plot minggu
        freq_weeks.plot(kind="bar", figsize=(9, 5), edgecolor="black")
        plt.ylabel("Frekuensi")
        plt.xlabel("Interval Antar Kunjungan")
        plt.title("Distribusi Interval Antar Kunjungan Pasien (Mingguan)")
        plt.grid(axis="y", alpha=0.3)
        plt.show()

    return intervals_df, freq_days, freq_weeks

def diuretik_egfr_combined(
    df_diuretik,
    df_egfr,
    diuretik_col="MR No. / Vendor Code",
    egfr_col="Medical Record No.",
    make_plot=False
):
    """
    1. Menghapus duplikasi MR pada masing-masing dataframe
    2. Menggabungkan pasien Diuretik & eGFR
    3. Menghitung distribusi frekuensi
    4. (Opsional) Membuat bar plot frekuensi
    """

  
    diuretik_unique = df_diuretik.drop_duplicates(subset=diuretik_col)
    egfr_unique = df_egfr.drop_duplicates(subset=egfr_col)

    print(f"Diuretik unik : {len(diuretik_unique)} pasien")
    print(f"eGFR unik  : {len(egfr_unique)} pasien")


    set_diuretik = set(diuretik_unique[diuretik_col].dropna())
    set_egfr = set(egfr_unique[egfr_col].dropna())

    both = set_diuretik & set_egfr
    only_diuretik = set_diuretik - set_egfr
    only_egfr = set_egfr - set_diuretik

 
    freq_dict = {
        "Diuretik only": len(only_diuretik),
        "eGFR only": len(only_egfr),
        "Both Diuretik & eGFR": len(both),
    }

    freq_df = pd.DataFrame.from_dict(freq_dict, orient="index", columns=["count"])

    print("\nDistribusi pasien:")
    print(freq_df)


    if make_plot:
        plt.figure(figsize=(6, 4))
        plt.bar(freq_df.index, freq_df["count"])
        plt.ylabel("Jumlah Pasien")
        plt.title("Distribusi Pasien Diuretik vs eGFR")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.show()

    df_both = pd.merge(
        diuretik_unique,
        egfr_unique,
        left_on=diuretik_col,
        right_on=egfr_col,
        how="inner"
    )

    print(f"\nJumlah pasien dengan Diuretik & eGFR: {len(df_both)}")

    return {
        "freq_df": freq_df,
        "df_both": df_both,
        "set_diuretik": set_diuretik,
        "set_egfr": set_egfr,
        "both": both
    }
    
def visit_interval_after_merge(
    df_both,
    patient_col="Medical Record No.",
    date_col="Order Date",
    make_plot=True
):
    """
    Menghitung distribusi interval kunjungan pasien
    SETELAH data Diuretik dan eGFR digabung.
    """

    df = df_both.copy()

    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")


    df = df.sort_values([patient_col, date_col])

    df["delta_days"] = (
        df.groupby(patient_col)[date_col]
        .diff()
        .dt.days
    )

    intervals = df["delta_days"].dropna()

    bins = [0, 14, 30, 60, 90, 180, 365, np.inf]

    labels = [
        "1–2 minggu",
        "2–4 minggu",
        "1–2 bulan",
        "2–3 bulan",
        "3–6 bulan",
        "6–12 bulan",
        ">12 bulan"
    ]

    interval_cat = pd.cut(intervals, bins=bins, labels=labels, right=True)

    freq = interval_cat.value_counts().reindex(labels)

    print("\nDistribusi interval kunjungan (pasien Diuretik + eGFR):")
    print(freq)


    if make_plot:
        plt.figure(figsize=(7, 4))
        plt.bar(freq.index.astype(str), freq.values)
        plt.ylabel("Jumlah Interval")
        plt.title("Distribusi Interval Kunjungan Pasien Diuretik + eGFR")
        plt.xticks(rotation=25)
        plt.tight_layout()
        plt.show()

    return freq, df    

def get_diuretik_egfr_longitudinal(
    df_diuretik,
    df_egfr,
    diuretik_col="MR No. / Vendor Code",
    egfr_col="Medical Record No."
):
    """
    Ambil seluruh riwayat eGFR untuk pasien yang pernah mendapat Diuretik.
    """

    # pasien Diuretik unik
    diuretik_patients = df_diuretik[diuretik_col].dropna().unique()

    # filter eGFR hanya pasien Diuretik
    df_egfr_filtered = df_egfr[
        df_egfr[egfr_col].isin(diuretik_patients)
    ].copy()

    print(f"Jumlah pasien Diuretik: {len(diuretik_patients)}")
    print(f"Jumlah baris eGFR untuk pasien Diuretik: {len(df_egfr_filtered)}")

    return df_egfr_filtered

if __name__ == "__main__":
    if 0: # Kode untuk Memfilter
        filter_excel_by_keyword(
        excel_files_pattern="D:\SKRIPSI\DATA RSUI\RAW STOCK CARD\SC *.xlsx",
        list_sortir=(
                 "FUROSEMID 40 MG TABLET",
                 "FUROSEMID 20 MG/2 ML INJECTION",
                 "ROXEMID 20 MG/2 ML INJ",
                 "LASIX 20 MG/2 ML INJECTION",
                 "SPIRONOLAKTON 100 MG TABLET",
                 "SPIRONOLAKTON 25 MG TABLET",
                 "CARPIATON 100 MG TABLET",
                 "HYDROCHLOROTHIAZIDE 25 MG TABLET"
                 ),
        )

        print("selesai")

    if 0: # Kode untuk menggabungkan
        excel_file_template = "SC {Bulan} Diuretik.xlsx"
        glob_pattern = f"D:\SKRIPSI\DATA RSUI\kurasiscdiuretik\{excel_file_template.replace('{Bulan}', '*')}"
        df_combined = load_and_combine_excel_data(glob_pattern)
        df_combined.to_excel("D:\SKRIPSI\DATA RSUI\kurasiscdiuretikcombined.xlsx")

        patient_visit_frequency(df_combined,
                                patient_col="Patient Name / Vendor Name", 
                                date_col="Created Date")


        print(df_combined.head())
        df_combined.info()
    
    if 1: # Analisis gabungan Diuretik & eGFR
        df_diuretik = pd.read_excel("D:\SKRIPSI\DATA RSUI\kurasiscdiuretikcombined.xlsx")
        df_egfr = pd.read_excel("D:\SKRIPSI\DATA RSUI\kurasiegfrcombined.xlsx")

        df_long = get_diuretik_egfr_longitudinal(df_diuretik, df_egfr)

        freq, df_interval = visit_interval_after_merge(
            df_long,
            patient_col="Patient Name",
            date_col="Order Date"
        )
        
        print("selesai")