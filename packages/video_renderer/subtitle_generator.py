import cv2
import numpy as np
import json
from PIL import Image, ImageDraw, ImageFont
from video_model.models import SubtitleElement

class SubtitleGenerator:
    """
    Processa um arquivo JSON de transcrição e desenha legendas estilizadas
    com formatação avançada, destaque de palavras e fundos.
    """
    def __init__(self, element: SubtitleElement, project_width: int, project_height: int):
        self.start = element.start
        self.end = element.end
        with open(element.path, 'r', encoding='utf-8') as f:
            self.dados_originais = json.load(f)

        # Atributos da Legenda
        self.posicao_legenda = element.position.lower()
        self.margem_vertical = element.margin_v
        self.max_linhas = element.max_lines
        self.max_palavras_linha = element.max_words
        self.largura_maxima = element.max_width
        self.fator_espacamento_linha = element.line_spacing_factor
        
        # Estilo da Fonte
        style = element.font
        self.caminho_fonte = style.get("path")
        self.tamanho_fonte = style.get("size", 40)
        self.tamanho_destaque = self.tamanho_fonte * style.get("highlight_scale",1)
        self.cor_fonte = style.get("color","#FFFFFF")
        self.cor_destaque = style.get("highlight_color","#FFFF00")
        # Contorno
        stroke = style.get("stroke", {})
        self.espessura_contorno = stroke.get("width",2)
        self.cor_contorno = stroke.get("color","#000000")
        # Sombra
        shadow = style.get("shadow",{})
        self.cor_sombra = tuple(shadow.get("color",[0,0,0,0.5]))
        self.deslocamento_sombra = tuple(shadow.get("offset",[0,0]))
        # Tempo
        timing = element.timing
        self.tempo_extra_visivel = timing.get("extra_time", 0.5)
        deslocamento_segundos=timing.get("offset", 0.0)
        fator_tempo=timing.get("speed_factor", 1.0)
        # Retangulo na palavra
        word_background = element.word_background
        self.habilitar_retangulo = word_background.get("enabled", False)
        self.cor_retangulo = tuple(word_background.get("color", [0,0,0,255]))
        self.padding_retangulo = tuple(word_background.get("padding", [8,8]))
        self.raio_borda_retangulo = word_background.get("radius", 10)
        shadow_word_background = word_background.get("shadow",{})
        self.sombra_retangulo_habilitar = shadow_word_background.get("enabled", True)
        self.sombra_retangulo_cor = tuple(shadow_word_background.get("color", [0,0,0,128]))
        self.sombra_retangulo_deslocamento = tuple(shadow_word_background.get("offset", [2,2]))

        self.fonte_principal = ImageFont.truetype(self.caminho_fonte, self.tamanho_fonte)
        self.fonte_destaque = ImageFont.truetype(self.caminho_fonte, self.tamanho_destaque)
        self.blocos_de_exibicao = self._pre_processar_blocos(deslocamento_segundos, fator_tempo)


     # ... Métodos de _ajustar a _obter_palavra_atual permanecem os mesmos ...
    def _ajustar_e_obter_palavras(self, deslocamento, fator):
        todas_as_palavras = []
        if fator <= 0: raise ValueError("O fator_tempo deve ser positivo.")
        for segmento in self.dados_originais['segments']:
            if 'words' in segmento and segmento['words']:
                for palavra in segmento['words']:
                    palavra_copia = palavra.copy()
                    palavra_copia['start'] = (palavra_copia['start'] / fator) + deslocamento
                    palavra_copia['end'] = (palavra_copia['end'] / fator) + deslocamento
                    todas_as_palavras.append(palavra_copia)
        return todas_as_palavras

    def _formatar_bloco_teste(self, palavras):
        linhas, linha_atual, largura_atual = [], [], 0
        largura_espaco = self.fonte_principal.getbbox(" ")[2]
        for palavra_info in palavras:
            largura_palavra = self.fonte_principal.getbbox(palavra_info['word'])[2]
            if ((self.max_palavras_linha and len(linha_atual) >= self.max_palavras_linha) or
                (self.largura_maxima and (largura_atual + largura_espaco + largura_palavra) > self.largura_maxima and linha_atual)):
                linhas.append(linha_atual)
                linha_atual, largura_atual = [], 0
            linha_atual.append(palavra_info)
            largura_atual += largura_palavra + (largura_espaco if len(linha_atual) > 1 else 0)
        if linha_atual: linhas.append(linha_atual)
        return linhas

    # MUDANÇA: Lógica de tempo de término ajustada aqui
    def _pre_processar_blocos(self, deslocamento, fator):
        todas_as_palavras = self._ajustar_e_obter_palavras(deslocamento, fator)
        if not todas_as_palavras: return []
        
        blocos_finais = []
        palavras_processadas_idx = 0
        while palavras_processadas_idx < len(todas_as_palavras):
            bloco_atual = []
            for i in range(palavras_processadas_idx, len(todas_as_palavras)):
                palavra = todas_as_palavras[i]
                bloco_temporario = bloco_atual + [palavra]
                linhas_formatadas = self._formatar_bloco_teste(bloco_temporario)
                if len(linhas_formatadas) > self.max_linhas:
                    if not bloco_atual: bloco_atual = [palavra]
                    break 
                else: bloco_atual = bloco_temporario
            
            if bloco_atual:
                # Calcula o tempo de término desejado com o tempo extra
                end_time_desejado = bloco_atual[-1]['end'] + self.tempo_extra_visivel
                
                # Verifica o tempo de início da próxima palavra para evitar sobreposição
                proximo_start_time = float('inf')
                indice_ultima_palavra_bloco = palavras_processadas_idx + len(bloco_atual) - 1
                if indice_ultima_palavra_bloco + 1 < len(todas_as_palavras):
                    proximo_start_time = todas_as_palavras[indice_ultima_palavra_bloco + 1]['start']
                
                # O tempo final é o menor entre o desejado e o início do próximo, garantindo que não haja sobreposição
                end_time_final = min(end_time_desejado, proximo_start_time)

                blocos_finais.append({
                    "start": bloco_atual[0]['start'], 
                    "end": end_time_final, 
                    "words": bloco_atual
                })
                palavras_processadas_idx += len(bloco_atual)
            else:
                 palavras_processadas_idx += 1
        return blocos_finais

    def _obter_bloco_ativo(self, tempo):
        for bloco in self.blocos_de_exibicao:
            # A condição de < end agora funciona perfeitamente com a nova lógica de tempo
            if bloco['start'] <= tempo < bloco['end']:
                return bloco
        return None

    def _obter_palavra_atual(self, bloco, tempo):
        if not bloco: return None
        palavra_exata, ultima_palavra_valida = None, None
        for palavra in bloco['words']:
            if palavra['start'] <= tempo <= palavra['end']:
                palavra_exata = palavra
                break
            if palavra['start'] <= tempo:
                ultima_palavra_valida = palavra
            else:
                break
        return palavra_exata if palavra_exata else ultima_palavra_valida

    def _desenhar_retangulo_arredondado(self, draw, xy, raio, fill):
        x1, y1, x2, y2 = xy
        if raio == 0:
            draw.rectangle(xy, fill=fill)
            return
        raio = min(raio, (x2 - x1) / 2, (y2 - y1) / 2)
        draw.pieslice([x1, y1, x1 + raio * 2, y1 + raio * 2], 180, 270, fill=fill)
        draw.pieslice([x2 - raio * 2, y1, x2, y1 + raio * 2], 270, 360, fill=fill)
        draw.pieslice([x1, y2 - raio * 2, x1 + raio * 2, y2], 90, 180, fill=fill)
        draw.pieslice([x2 - raio * 2, y2 - raio * 2, x2, y2], 0, 90, fill=fill)
        draw.rectangle([x1 + raio, y1, x2 - raio, y2], fill=fill)
        draw.rectangle([x1, y1 + raio, x2, y2 - raio], fill=fill)

    def desenhar_legenda(self, frame, palavras_do_bloco, palavra_atual, altura_video):
        linhas = self._formatar_bloco_teste(palavras_do_bloco)
        if not linhas: return frame
        
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil, "RGBA")
        
        largura_espaco = self.fonte_principal.getbbox(" ")[2]
        
        alturas_das_linhas = []
        for linha in linhas:
            tem_destaque = palavra_atual in linha
            fonte_para_altura = self.fonte_destaque if tem_destaque else self.fonte_principal
            altura_base_linha = fonte_para_altura.getbbox("Tg")[3]
            altura_final_linha = altura_base_linha * self.fator_espacamento_linha
            alturas_das_linhas.append(altura_final_linha)

        altura_total_real = sum(alturas_das_linhas)

        if self.posicao_legenda == 'superior':
            y_cursor = self.margem_vertical
        elif self.posicao_legenda == 'central':
            y_cursor = (altura_video / 2) - (altura_total_real / 2) + self.margem_vertical
        else:
            y_cursor = altura_video - altura_total_real - self.margem_vertical

        y_pass_1 = y_cursor
        for i, linha in enumerate(linhas):
            if self.habilitar_retangulo and palavra_atual in linha:
                largura_total_linha = sum(
                    (self.fonte_destaque if p == palavra_atual else self.fonte_principal).getbbox(p['word'])[2] for p in linha
                ) + largura_espaco * (len(linha) - 1)
                x_cursor = (frame.shape[1] - largura_total_linha) / 2
                
                for p_info in linha:
                    if p_info == palavra_atual: break
                    fonte_p = self.fonte_destaque if p_info == palavra_atual else self.fonte_principal
                    x_cursor += fonte_p.getbbox(p_info['word'])[2] + largura_espaco
                
                caixa = draw.textbbox((x_cursor, y_pass_1), palavra_atual['word'], font=self.fonte_destaque)
                px, py = self.padding_retangulo
                coords_retangulo = [caixa[0] - px, caixa[1] - py, caixa[2] + px, caixa[3] + py]

                if self.sombra_retangulo_habilitar:
                    dx, dy = self.sombra_retangulo_deslocamento
                    coords_sombra = [c + d for c, d in zip(coords_retangulo, [dx, dy, dx, dy])]
                    self._desenhar_retangulo_arredondado(draw, coords_sombra, self.raio_borda_retangulo, fill=self.sombra_retangulo_cor)
                
                self._desenhar_retangulo_arredondado(draw, coords_retangulo, self.raio_borda_retangulo, fill=self.cor_retangulo)
            
            y_pass_1 += alturas_das_linhas[i]

        y_pass_2 = y_cursor
        for i, linha in enumerate(linhas):
            largura_total_linha = sum(
                (self.fonte_destaque if p == palavra_atual else self.fonte_principal).getbbox(p['word'])[2] for p in linha
            ) + largura_espaco * (len(linha) - 1)
            x_linha = (frame.shape[1] - largura_total_linha) / 2
            
            for palavra_info in linha:
                palavra = palavra_info['word']
                destaque = (palavra_info == palavra_atual)
                fonte = self.fonte_destaque if destaque else self.fonte_principal
                cor = self.cor_destaque if destaque else self.cor_fonte
                
                if self.cor_sombra:
                    dx, dy = self.deslocamento_sombra
                    draw.text((x_linha + dx, y_pass_2 + dy), palavra, font=fonte, fill=self.cor_sombra)
                
                draw.text((x_linha, y_pass_2), palavra, font=fonte, fill=cor, stroke_width=self.espessura_contorno, stroke_fill=self.cor_contorno)
                
                largura_palavra = fonte.getbbox(palavra)[2]
                x_linha += largura_palavra + largura_espaco
            
            y_pass_2 += alturas_das_linhas[i]
            
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def processar(self, get_frame, t):
        frame_original = get_frame(t)
        if t > self.end: return frame_original
        t -= self.start
        frame_bgr = cv2.cvtColor(frame_original, cv2.COLOR_RGB2BGR)
        
        bloco_ativo = self._obter_bloco_ativo(t)
        
        if bloco_ativo:
            palavra_atual = self._obter_palavra_atual(bloco_ativo, t)
            frame_bgr = self.desenhar_legenda(
                frame_bgr, 
                bloco_ativo['words'], 
                palavra_atual, 
                frame_bgr.shape[0]
            )
        
        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    
    def apply_to_clip(self, clip):
       return clip.transform(self.processar)