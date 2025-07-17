import { Module } from '@nestjs/common';
import { ScrapingModule } from './scraping/scraping.module';
import { AwsModule } from './aws/aws.module';
import { GlueModule } from './glue/glue.module';

@Module({
  imports: [ScrapingModule, AwsModule, GlueModule],
})
export class AppModule {}
