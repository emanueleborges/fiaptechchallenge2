// scraping.service.ts
import { Injectable } from '@nestjs/common';
import axios from 'axios';
import { parse } from 'node-html-parser';
import * as fs from 'fs';

@Injectable()
export class ScrapingService {
  private readonly url = 'https://sistemaswebb3-listados.b3.com.br/indexPage/day/IBOV?language=pt-br';

  async fetchB3Data(): Promise<any[]> {
    const res = await axios.get(this.url);
    const html = parse(res.data);
    const table = html.querySelector('table');
    const rows = table.querySelectorAll('tr');

    const data = rows.slice(1).map(row => {
      const cols = row.querySelectorAll('td');
      return {
        codigo: cols[0]?.text.trim(),
        nome: cols[1]?.text.trim(),
        precoFechamento: parseFloat(cols[2]?.text.replace(',', '.')),
        data: new Date().toISOString().split('T')[0],
      };
    });

    fs.writeFileSync(`b3_data_${Date.now()}.json`, JSON.stringify(data, null, 2));
    return data;
  }
}
