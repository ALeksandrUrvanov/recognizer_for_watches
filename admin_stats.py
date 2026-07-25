import pandas as pd
import os
from config import LOG_CSV_PATH


def display_stats():
    """Выводит статистику распознавания часов"""
    
    if not os.path.exists(LOG_CSV_PATH):
        print(f"Файл логов не найден: {LOG_CSV_PATH}")
        return
    
    df = pd.read_csv(LOG_CSV_PATH)
    
    if len(df) == 0:
        print("Запросов пока нет")
        return
    
    completed = df[~df['selected_option'].isin(['pending', 'timeout'])]
    
    print(f"\nВсего запросов: {len(df)}")
    print(f"Завершенных: {len(completed)}")
    print(f"Ожидающих ответа: {len(df[df['selected_option'] == 'pending'])}")
    print(f"Таймаут: {len(df[df['selected_option'] == 'timeout'])}")
    
    if len(completed) > 0:
        print()
        
        # Конвертируем selected_option в строку для корректного сравнения
        completed['selected_option'] = completed['selected_option'].astype(str)
        
        top1 = len(completed[completed['selected_option'] == '1'])
        top2 = len(completed[completed['selected_option'].isin(['1','2'])])
        top3 = len(completed[completed['selected_option'].isin(['1','2','3'])])
        top4 = len(completed[completed['selected_option'].isin(['1','2','3','4'])])
        top5 = len(completed[completed['selected_option'].isin(['1','2','3','4','5'])])
        not_found = len(completed[completed['selected_option'] == '0'])
        
        print(f"Top-1 Accuracy: {top1/len(completed)*100:.1f}% ({top1} из {len(completed)})")
        print(f"Top-2 Accuracy: {top2/len(completed)*100:.1f}% ({top2} из {len(completed)})")
        print(f"Top-3 Accuracy: {top3/len(completed)*100:.1f}% ({top3} из {len(completed)})")
        print(f"Top-4 Accuracy: {top4/len(completed)*100:.1f}% ({top4} из {len(completed)})")
        print(f"Top-5 Accuracy: {top5/len(completed)*100:.1f}% ({top5} из {len(completed)})")
        print(f"Не найдено: {not_found} ({not_found/len(completed)*100:.1f}%)")
        
        print()
        avg_processing = df['processing_time'].astype(float).mean()
        print(f"Среднее время обработки: {avg_processing:.2f} сек")
        
        if 'response_time' in completed.columns:
            valid_response = completed[completed['response_time'] != '']
            if len(valid_response) > 0:
                avg_response = valid_response['response_time'].astype(float).mean()
                print(f"Среднее время ответа товароведа: {avg_response:.1f} сек")
        
        print()
        user_stats = completed.groupby('user_id').size().sort_values(ascending=False)
        for user_id, count in user_stats.head(5).items():
            user_data = completed[completed['user_id'] == user_id]
            user_top5 = len(user_data[user_data['selected_option'].isin(['1','2','3','4','5'])])
            accuracy = user_top5 / len(user_data) * 100
            print(f"User {user_id}: {count} запросов, Top-5: {accuracy:.1f}%")
        
        print()
        selection_counts = completed['selected_option'].value_counts().sort_index()
        for option, count in selection_counts.items():
            percentage = count / len(completed) * 100
            bar = "█" * int(percentage / 2)
            print(f"Вариант {option}: {count:3d} ({percentage:5.1f}%) {bar}")
    
    print()


if __name__ == "__main__":
    display_stats()

