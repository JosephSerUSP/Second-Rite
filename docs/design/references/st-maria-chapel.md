# St. Maria Chapel: architectural references

Reference for authoring Sister Agnes's chapel (`tools/blender/recipes/st_maria_chapel.py`)
and any small St. Maria church: a limewashed colonial Portuguese chapel on an island
town square. Every image is on Wikimedia Commons under the licence listed; follow the
link for the full-size file and its terms. The composite contact sheet is a review
artefact regenerated into `out/reference/` and is not committed:

```text
python tools/reference-sheets/fetch_commons.py   # licensed candidates + manifest
python tools/reference-sheets/make_sheet.py      # out/reference/st_maria_chapel_references.png
python tools/reference-sheets/make_doc.py        # this file
```

## What the references say about this chapel

- **The model room is Nossa Senhora do Rosario, Cidade Velha (Cape Verde, 1495)**, the
  oldest colonial church in the tropics and an island church: limewashed walls, an
  azulejo dado to the window sills, pews in two banks, a red carpet down the aisle,
  one step across the nave at the altar end (1-2). The St. Maria chapel follows it.
- **The roof is pitched timber, not a flat beamed ceiling** (1, 2, 5). `Interior.ceiling`
  can only build a flat ceiling with beams; a pitched roof is a missing axis.
- **The carpet is red** in every nave that has one (1, 7, 8). The material registry has
  no red cloth, so the chapel's runner uses `aged_cloth` with a terracotta border.
- **The way out is a door in the long wall** (3, 4, 12): an arched opening in a stone
  frame, set into thick limewash, with dark panelled leaves (9-11). The chapel's door is
  in the far wall; its frame is still plain.
- **Seen from a corner, the pews cut the foreground on a diagonal** (5, 6). That is the
  camera this room is reviewed with: yawed off the aisle, not square to it.
- **Gilt is a frame, not a surface** (13, 14): a dark centre inside gold carving. The
  `altar` retable does this; its recess is still empty by design.
- **Fonts stand by the door**, on a turned column or let into the wall (15, 16).
- **Island chapels are small and worn** (17, 18): salt-stained limewash, blue in the
  apse, light from few openings.

## Credits

| # | Teaches | Source | Author | Licence |
|---|---|---|---|---|
| 1 | Nave: limewash, azulejo dado, timber roof, red carpet, pews both sides | [Igreja de Nossa Senhora do Rosário (Cidade Velha) 05.jpg](https://commons.wikimedia.org/wiki/File:Igreja_de_Nossa_Senhora_do_Ros%C3%A1rio_(Cidade_Velha)_05.jpg) | GualdimG | CC BY-SA 4.0 |
| 2 | Altar end: one step across the nave, side altars, tile to the sill | [Cape Verde Cidade Velha Nossa Senhora do Rosario 2011.jpg](https://commons.wikimedia.org/wiki/File:Cape_Verde_Cidade_Velha_Nossa_Senhora_do_Rosario_2011.jpg) | Cayambe | CC BY-SA 3.0 |
| 3 | Outside: limewash over stone quoins, buttress, arched side door | [Cidade Velha Nossa Senhora do Rosário ext 2011.jpg](https://commons.wikimedia.org/wiki/File:Cidade_Velha_Nossa_Senhora_do_Ros%C3%A1rio_ext_2011.jpg) | Cayambe | CC BY-SA 3.0 |
| 4 | Side door in the long wall: stone frame in whitewash | [Cidade Velha-Igreja Nossa Senhora do Rosário (1).jpg](https://commons.wikimedia.org/wiki/File:Cidade_Velha-Igreja_Nossa_Senhora_do_Ros%C3%A1rio_(1).jpg) | Ji-Elle | CC BY-SA 3.0 |
| 5 | Rosario from a corner: pews cut the foreground diagonally | [Cidade Velha - Nossa Senhora do Rosário church 2014-10-02.jpg](https://commons.wikimedia.org/wiki/File:Cidade_Velha_-_Nossa_Senhora_do_Ros%C3%A1rio_church_2014-10-02.jpg) | Reino Baptista | CC BY-SA 4.0 |
| 6 | Remedios, Peniche: pews in front, tall tile panel beyond | [Azulejos do lado direito no interior da Igreja de Nossa Senhora dos Remédios, também denominada «Ermida de Nossa Senhora dos Remédios» ou «Santuário da Senhora dos Remédios».jpg](https://commons.wikimedia.org/wiki/File:Azulejos_do_lado_direito_no_interior_da_Igreja_de_Nossa_Senhora_dos_Rem%C3%A9dios,_tamb%C3%A9m_denominada_%C2%ABErmida_de_Nossa_Senhora_dos_Rem%C3%A9dios%C2%BB_ou_%C2%ABSantu%C3%A1rio_da_Senhora_dos_Rem%C3%A9dios%C2%BB.jpg) | Threeohsix | CC BY-SA 4.0 |
| 7 | Sesimbra: carpet aisle leading the eye to the altar | [Igreja Matriz de Sesimbra - Portugal (50684421716).jpg](https://commons.wikimedia.org/wiki/File:Igreja_Matriz_de_Sesimbra_-_Portugal_(50684421716).jpg) | Vitor Oliveira from Torres Vedras, PORTUGAL | CC BY-SA 2.0 |
| 8 | Rans: carpet + gilt retable as the far focal point | [Igreja de São Tomé - Rans 2.jpg](https://commons.wikimedia.org/wiki/File:Igreja_de_S%C3%A3o_Tom%C3%A9_-_Rans_2.jpg) | Alegna13 | CC BY-SA 3.0 |
| 9 | Sardoal: round-arched stone frame, dark panelled leaves | [Porta lateral da Igreja da Misericórdia, Sardoal 1.jpg](https://commons.wikimedia.org/wiki/File:Porta_lateral_da_Igreja_da_Miseric%C3%B3rdia,_Sardoal_1.jpg) | see source | CC BY 2.0 |
| 10 | Elvas: carved limestone surround, worn threshold | [- 65 - PORTA LATERAL - Igreja de Nossa Senhora da Assunção – XVIII - ELVAS – ALENTEJO - PORTUGAL (4568158218).jpg](https://commons.wikimedia.org/wiki/File:-_65_-_PORTA_LATERAL_-_Igreja_de_Nossa_Senhora_da_Assun%C3%A7%C3%A3o_%E2%80%93_XVIII_-_ELVAS_%E2%80%93_ALENTEJO_-_PORTUGAL_(4568158218).jpg) | Celestino Manuel from Vendas Novas, Portugal | CC BY 2.0 |
| 11 | Carmo: carved panelled leaves in a tiled surround | [Igreja do Carmo (porta lateral 2).JPG](https://commons.wikimedia.org/wiki/File:Igreja_do_Carmo_(porta_lateral_2).JPG) | Béria Lima de Rodríguez | CC BY-SA 3.0 |
| 12 | Almoster: side door in the long wall, set deep | [Porta na lateral direita da Igreja Paroquial de Almoster.jpg](https://commons.wikimedia.org/wiki/File:Porta_na_lateral_direita_da_Igreja_Paroquial_de_Almoster.jpg) | Threeohsix | CC BY-SA 4.0 |
| 13 | Talha dourada retable: gilt frame round a dark centre | [Igreja da Graça - Torres Vedras - Portugal (51295931376).jpg](https://commons.wikimedia.org/wiki/File:Igreja_da_Gra%C3%A7a_-_Torres_Vedras_-_Portugal_(51295931376).jpg) | Vitor Oliveira from Torres Vedras, PORTUGAL | CC BY-SA 2.0 |
| 14 | Side altar: retable over an azulejo dado | [Igreja da Graça - Torres Vedras - Portugal (51295926981).jpg](https://commons.wikimedia.org/wiki/File:Igreja_da_Gra%C3%A7a_-_Torres_Vedras_-_Portugal_(51295926981).jpg) | Vitor Oliveira from Torres Vedras, PORTUGAL | CC BY-SA 2.0 |
| 15 | Holy-water font on a turned column (Salvador, Brazil) | [Igreja da Ordem Terceira de São Francisco Salvador Pia de Água Benta 2018-0371.jpg](https://commons.wikimedia.org/wiki/File:Igreja_da_Ordem_Terceira_de_S%C3%A3o_Francisco_Salvador_Pia_de_%C3%81gua_Benta_2018-0371.jpg) | Paul R. Burley | CC BY-SA 4.0 |
| 16 | Wall font with a shell back | [Pia de água benta - Carragosa.jpg](https://commons.wikimedia.org/wiki/File:Pia_de_%C3%A1gua_benta_-_Carragosa.jpg) | see source | CC BY 2.0 |
| 17 | Baluarte, Ilha de Mocambique: small, weathered, island light | [Capela de Nossa Senhora do Baluarte, Ilha de Moçambique (1).jpg](https://commons.wikimedia.org/wiki/File:Capela_de_Nossa_Senhora_do_Baluarte,_Ilha_de_Mo%C3%A7ambique_(1).jpg) | Jcornelius | CC BY-SA 4.0 |
| 18 | Santo Antonio, Ilha de Mocambique: blue apse, white nave | [Capela Santo Antonio ilha mozambique.jpg](https://commons.wikimedia.org/wiki/File:Capela_Santo_Antonio_ilha_mozambique.jpg) | Rosino | CC BY-SA 2.0 |
| 19 | Ermida da Memoria, Nazare: tile to the vault in a tiny chapel | [Interior da Ermida da Memória em 2022.jpg](https://commons.wikimedia.org/wiki/File:Interior_da_Ermida_da_Mem%C3%B3ria_em_2022.jpg) | Threeohsix | CC BY-SA 4.0 |
| 20 | Guia, Macau: vault and door seen from within | [Nossa Senhora da Guia Churche.jpg](https://commons.wikimedia.org/wiki/File:Nossa_Senhora_da_Guia_Churche.jpg) | The original uploader was Iidxplus at Chinese Wikipedia. | CC BY-SA 2.0 |
| 21 | Corpo Santo, Funchal: fishermen's chapel on an island square | [Funchal (Madeira, Portugal), Capela do Corpo Santo -- 2025 -- 1175.jpg](https://commons.wikimedia.org/wiki/File:Funchal_(Madeira,_Portugal),_Capela_do_Corpo_Santo_--_2025_--_1175.jpg) | Dietmar Rabich | CC BY-SA 4.0 |
| 22 | Ermida de Sao Juliao: white chapel above the sea | [Ermida de São Julião - Praia de São Julião - Portugal (7149358769).jpg](https://commons.wikimedia.org/wiki/File:Ermida_de_S%C3%A3o_Juli%C3%A3o_-_Praia_de_S%C3%A3o_Juli%C3%A3o_-_Portugal_(7149358769).jpg) | Vitor Oliveira from Torres Vedras, PORTUGAL | CC BY-SA 2.0 |

