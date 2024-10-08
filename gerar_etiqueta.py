import requests
import time
from io import BytesIO
from PyPDF2 import PdfMerger

def read_zpl_file(zpl_file_path):
    """
    Função para ler um arquivo de texto com comandos ZPL e separá-los em etiquetas.
    """
    try:
        with open(zpl_file_path, 'r', encoding='utf-8') as file:
            zpl_data = file.read()
        # Separar as etiquetas com base no comando ^FS^XZ (final da etiqueta)
        zpl_labels = zpl_data.split('^FS^XZ')
        # Reanexar o comando ^FS^XZ ao final de cada etiqueta
        zpl_labels = [label.strip() + '^FS^XZ' for label in zpl_labels if label.strip()]
        print(f"{len(zpl_labels)} etiquetas encontradas no arquivo.")  # Debug para contar etiquetas
        return zpl_labels
    except Exception as e:
        print(f"Erro ao ler o arquivo ZPL: {e}")
        return None

def generate_label_pdf(zpl_data_list, width_in_inches=4, height_in_inches=6):
    """
    Função para enviar várias etiquetas ZPL para a API do Labelary e gerar um único PDF com várias páginas.
    """
    if zpl_data_list is None:
        print("Nenhum dado ZPL foi encontrado.")
        return

    rate_limit = 5  # Limite de requisições por segundo
    requests_made = 0
    start_time = time.time()
    pdf_merger = PdfMerger()  # Para combinar os PDFs

    for index, zpl_data in enumerate(zpl_data_list):
        retry_attempts = 0
        success = False

        while not success:
            # Verificar se a etiqueta contém conteúdo ZPL válido
            if not zpl_data.strip():  # Se a string ZPL estiver vazia
                print(f"Etiqueta {index + 1} está vazia ou mal formada. Ignorando.")
                break

            print(f"Processando etiqueta {index + 1} (tentativa {retry_attempts + 1}):")

            url = f"http://api.labelary.com/v1/printers/8dpmm/labels/{width_in_inches}x{height_in_inches}/"
            headers = {'Accept': 'application/pdf'}

            try:
                response = requests.post(url, headers=headers, data=zpl_data.encode('utf-8'))

                if response.status_code == 200:
                    # Adicionar o conteúdo PDF ao PdfMerger
                    pdf_merger.append(BytesIO(response.content))
                    print(f"PDF gerado com sucesso para a etiqueta {index + 1}.")
                    success = True  # A requisição foi bem-sucedida
                elif response.status_code == 429:
                    retry_attempts += 1
                    print(f"Limite de requisições excedido. Aguardando 5 segundos antes de tentar novamente...")
                    time.sleep(5)  # Pausa por 5 segundos quando o limite é excedido
                else:
                    print(f"Erro ao gerar o PDF para a etiqueta {index + 1}: {response.status_code} - {response.text}")
                    success = True  # Considera que houve erro não relacionado ao limite e continua

            except Exception as e:
                print(f"Erro ao acessar a API do Labelary para a etiqueta {index + 1}: {e}")
                success = True  # Continua no loop em caso de exceção não tratada

        # Incrementa o contador de requisições
        requests_made += 1

        # Verifica se atingiu o limite de requisições por segundo
        if requests_made >= rate_limit:
            elapsed_time = time.time() - start_time
            if elapsed_time < 1:
                time.sleep(1 - elapsed_time)  # Espera até completar 1 segundo
            requests_made = 0
            start_time = time.time()

    # Salvar o PDF consolidado se houver conteúdo
    with open("combined_labels.pdf", "wb") as f:
        pdf_merger.write(f)
        pdf_merger.close()
    print("PDF consolidado gerado com sucesso! Verifique o arquivo 'combined_labels.pdf'")

# Exemplo de uso:
zpl_file_path = r"C:\Users\User\Downloads\etiquetas\thermal_zpl_shipping_label.txt"  # Caminho do arquivo ZPL
zpl_data_list = read_zpl_file(zpl_file_path)  # Ler o arquivo ZPL e dividir em etiquetas
generate_label_pdf(zpl_data_list)  # Gera um PDF único com várias páginas
