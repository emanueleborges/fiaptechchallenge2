// app.controller.ts
import { Controller, Get } from '@nestjs/common';
import { ScrapingService } from './scraping/scraping.service';
import { AwsService } from './aws/aws.service';
import { GlueService } from './glue/glue.service';

@Controller()
export class AppController {
  constructor(
    private scraping: ScrapingService,
    private aws: AwsService,
    private glue: GlueService,
  ) {}

  @Get('/run')
  async run() {
    const data = await this.scraping.fetchB3Data();
    const filePath = `b3_data_${Date.now()}.json`;
    const bucket = process.env.S3_BUCKET;
    const key = `raw/${filePath}`;
    
    await this.aws.uploadToS3(filePath, bucket, key);
    await this.glue.startJob(process.env.GLUE_JOB_NAME);

    return { status: 'Success' };
  }
}
