import os
import requests
import zipfile
import pandas as pd
from datasets import Dataset, DatasetDict

def download_cmmlu_dataset():
    """
    Download CMMLU dataset directly từ Hugging Face ZIP file
    """
    print("🚀 Downloading CMMLU dataset from official source...")
    
    # Tạo thư mục data nếu chưa có
    os.makedirs("data/teacher_data", exist_ok=True)
    
    # URL của CMMLU ZIP file
    zip_url = "https://huggingface.co/datasets/haonan-li/cmmlu/resolve/main/cmmlu_v1_0_1.zip"
    zip_path = "data/teacher_data/cmmlu_v1_0_1.zip"
    extract_path = "data/teacher_data/cmmlu_extracted"
    
    try:
        # Download ZIP file
        print("📥 Downloading ZIP file...")
        response = requests.get(zip_url, stream=True)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("✅ ZIP file downloaded successfully")
        
        # Extract ZIP file
        print("📂 Extracting ZIP file...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        print("✅ Files extracted successfully")
        
        # List extracted files
        print("\n📋 Available subjects:")
        dev_path = os.path.join(extract_path, "dev")
        test_path = os.path.join(extract_path, "test")
        
        if os.path.exists(dev_path):
            subjects = [f.replace('.csv', '') for f in os.listdir(dev_path) if f.endswith('.csv')]
            print(f"Found {len(subjects)} subjects")
            for i, subject in enumerate(subjects[:10], 1):
                print(f"{i:2d}. {subject}")
            if len(subjects) > 10:
                print(f"    ... and {len(subjects) - 10} more")
        
        # Load ALL subjects
        print(f"\n📊 Loading ALL {len(subjects)} subjects...")
        all_datasets = load_all_subjects(extract_path, subjects)
        
        if all_datasets:
            # Merge all subjects into one big dataset
            merged_dataset = merge_all_subjects(all_datasets)
            
            if merged_dataset:
                # Save merged dataset
                merged_dataset.save_to_disk("data/teacher_data/cmmlu_all_subjects")
                print("✅ All subjects merged and saved")
                return merged_dataset, subjects
            else:
                print("⚠️  Merge failed, but individual subjects are saved")
                # Return first successful dataset as sample
                first_subject = list(all_datasets.keys())[0]
                return all_datasets[first_subject], subjects
        else:
            print("❌ Failed to load subjects")
            return None, subjects
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None, []
    except zipfile.BadZipFile as e:
        print(f"❌ ZIP file error: {e}")
        return None, []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None, []

def load_subject_from_csv(extract_path, subject):
    """
    Load specific subject từ CSV files với data cleaning
    """
    dev_file = os.path.join(extract_path, "dev", f"{subject}.csv")
    test_file = os.path.join(extract_path, "test", f"{subject}.csv")
    
    datasets = {}
    
    # Load dev set
    if os.path.exists(dev_file):
        dev_df = pd.read_csv(dev_file)
        dev_df = clean_dataframe(dev_df, subject, "dev")
        datasets['dev'] = Dataset.from_pandas(dev_df)
        print(f"✅ Dev set loaded: {len(dev_df)} samples")
    
    # Load test set  
    if os.path.exists(test_file):
        test_df = pd.read_csv(test_file)
        test_df = clean_dataframe(test_df, subject, "test")
        datasets['test'] = Dataset.from_pandas(test_df)
        print(f"✅ Test set loaded: {len(test_df)} samples")
    
    return DatasetDict(datasets)

def clean_dataframe(df, subject, split):
    """
    Clean dataframe - fix NaN values và data types
    """
    # Replace NaN values với empty string
    df = df.fillna("")
    
    # Ensure all columns are strings
    for col in ['Question', 'A', 'B', 'C', 'D', 'Answer']:
        if col in df.columns:
            df[col] = df[col].astype(str)
    
    # Remove rows where Question is empty
    df = df[df['Question'].str.strip() != ""]
    
    # Validate Answer column (should be A, B, C, or D)
    if 'Answer' in df.columns:
        valid_answers = df['Answer'].str.strip().isin(['A', 'B', 'C', 'D'])
        if not valid_answers.all():
            print(f"⚠️  Warning: {subject} {split} has {(~valid_answers).sum()} invalid answers")
            # Keep only valid answers
            df = df[valid_answers]
    
    return df

def load_all_subjects(extract_path, subjects):
    """
    Load TẤT CẢ subjects từ extracted CSV files
    """
    print(f"📚 Loading ALL {len(subjects)} subjects...")
    
    all_datasets = {}
    success_count = 0
    
    for i, subject in enumerate(subjects, 1):
        try:
            print(f"[{i}/{len(subjects)}] Loading {subject}...")
            dataset_dict = load_subject_from_csv(extract_path, subject)
            
            if dataset_dict:
                all_datasets[subject] = dataset_dict
                success_count += 1
                print(f"✅ {subject} loaded ({len(dataset_dict.get('test', []))} test samples)")
            
        except Exception as e:
            print(f"❌ Failed to load {subject}: {e}")
            continue
    
    print(f"\n📊 Final Summary: {success_count}/{len(subjects)} subjects loaded successfully")
    return all_datasets

def merge_all_subjects(all_datasets):
    """
    Merge tất cả subjects thành 1 dataset lớn với error handling
    """
    print("🔗 Merging all subjects into one dataset...")
    
    all_dev_data = []
    all_test_data = []
    
    for subject_name, dataset_dict in all_datasets.items():
        try:
            # Add subject name to each sample
            if 'dev' in dataset_dict:
                dev_data = dataset_dict['dev'].to_pandas()
                dev_data['subject'] = subject_name
                dev_data['split'] = 'dev'
                # Clean data again before merging
                dev_data = clean_dataframe(dev_data, subject_name, 'dev')
                all_dev_data.append(dev_data)
            
            if 'test' in dataset_dict:
                test_data = dataset_dict['test'].to_pandas()
                test_data['subject'] = subject_name  
                test_data['split'] = 'test'
                # Clean data again before merging
                test_data = clean_dataframe(test_data, subject_name, 'test')
                all_test_data.append(test_data)
                
        except Exception as e:
            print(f"⚠️  Warning: Failed to process {subject_name}: {e}")
            continue
    
    # Combine all data
    merged_datasets = {}
    
    try:
        if all_dev_data:
            merged_dev = pd.concat(all_dev_data, ignore_index=True)
            # Final cleaning
            merged_dev = merged_dev.fillna("")
            for col in merged_dev.columns:
                merged_dev[col] = merged_dev[col].astype(str)
            
            merged_datasets['dev'] = Dataset.from_pandas(merged_dev)
            print(f"✅ Merged dev set: {len(merged_dev)} samples from {len(all_dev_data)} subjects")
        
        if all_test_data:
            merged_test = pd.concat(all_test_data, ignore_index=True)
            # Final cleaning
            merged_test = merged_test.fillna("")
            for col in merged_test.columns:
                merged_test[col] = merged_test[col].astype(str)
            
            merged_datasets['test'] = Dataset.from_pandas(merged_test)
            print(f"✅ Merged test set: {len(merged_test)} samples from {len(all_test_data)} subjects")
        
        return DatasetDict(merged_datasets)
        
    except Exception as e:
        print(f"❌ Error merging datasets: {e}")
        print("🔄 Trying to save successful subjects individually...")
        
        # Save individual subjects instead
        saved_subjects = []
        for subject_name, dataset_dict in all_datasets.items():
            try:
                subject_path = f"data/teacher_data/subjects/{subject_name}"
                os.makedirs(os.path.dirname(subject_path), exist_ok=True)
                dataset_dict.save_to_disk(subject_path)
                saved_subjects.append(subject_name)
            except Exception as e2:
                print(f"⚠️  Failed to save {subject_name}: {e2}")
        
        print(f"✅ Saved {len(saved_subjects)} subjects individually")
        return None

def preview_dataset(dataset_dict, total_subjects=67):
    """
    Preview merged dataset content
    """
    print(f"\n🔍 Complete CMMLU Dataset Preview:")
    print(f"Total subjects loaded: {total_subjects}")
    print(f"Dataset splits: {list(dataset_dict.keys())}")
    
    for split_name, split_data in dataset_dict.items():
        print(f"\n{split_name} split: {len(split_data)} samples")
        
        # Show subjects distribution
        if 'subject' in split_data.column_names:
            subjects_count = {}
            for item in split_data:
                subj = item['subject']
                subjects_count[subj] = subjects_count.get(subj, 0) + 1
            
            print(f"Subjects in {split_name}: {len(subjects_count)}")
            # Show top 5 subjects by sample count
            top_subjects = sorted(subjects_count.items(), key=lambda x: x[1], reverse=True)[:5]
            for subj, count in top_subjects:
                print(f"  - {subj}: {count} samples")
        
        # Print first sample
        if len(split_data) > 0:
            sample = split_data[0]
            print(f"\nSample from {split_name}:")
            for key, value in sample.items():
                if key in ['Question', 'A', 'B', 'C', 'D', 'Answer', 'subject']:
                    print(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
            break

def main():
    """
    Main function
    """
    print("=== CMMLU Dataset Direct Download ===\n")
    
    # Download and extract dataset
    dataset, available_subjects = download_cmmlu_dataset()
    
    if dataset and available_subjects:
        print("\n✅ COMPLETE CMMLU Dataset download completed!")
        
        # Preview complete dataset
        preview_dataset(dataset, len(available_subjects))
        
        print(f"\n💡 Dataset Information:")
        print(f"- Complete CMMLU dataset: data/teacher_data/cmmlu_all_subjects")
        print(f"- Raw CSV files: data/teacher_data/cmmlu_extracted") 
        print(f"- Total subjects loaded: {len(available_subjects)}")
        print(f"- Each subject has ~5 dev + ~100 test questions")
        print(f"- Total questions: ~{len(available_subjects) * 105} questions")
        
        # Calculate total questions
        if 'test' in dataset and 'dev' in dataset:
            total_questions = len(dataset['test']) + len(dataset['dev'])
            print(f"- Actual total questions loaded: {total_questions}")
        
        print(f"\n🎯 Ready for Kimi K2 testing!")
        
    else:
        print("\n❌ Dataset download failed!")
        print("💡 Fallback options:")
        print("1. Check internet connection")
        print("2. Try manual download from: https://github.com/haonan-li/CMMLU")
        print("3. Use alternative dataset like C-Eval")

if __name__ == "__main__":
    main()