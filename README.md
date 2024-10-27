# b3_crawler
Responsável por navegar pela B3 e obter o extrato de movimentação.


## Changelog

### v1.1.0

- Implementado tentativa de `async` no processamento da transação.

- Implementado tempo de execução do processamento da transação;
- Adicionado `driver.quit()` ao finalizar navegação com sucesso;
- Adicionado parâmetro `raise_error` na função `get_element_by_class`;
- Adicionado mais logs de execução da aplicação;
- Adicionado `return` na função `click_element`;
- Alterado função `abrir_tela_movimentacao` para utilizar a função `click_element` em vários pontos;
- Criado arquivo `constants.py`.

### v1.0.0

- Primeiro commit funcional, navegando e salvando JSON.
